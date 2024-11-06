import json
import pulumi
import pulumi_gcp as gcp
import pulumi_random as random
from pulumi_command import local
import re

from ..constants import DAYS

VAULT_IMAGE = "docker.io/hashicorp/vault:1.18.0@sha256:e2da7099950443e234ed699940fabcdc44b5babe33adfb459e189a63b7bb50d7"

class Vault(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                subdomain: str,
                dns_zone: str,
                opts = None):
        
        # Set and validate inputs
        self.name = name
        self.subdomain = subdomain
        self.dns_zone = dns_zone
        super().__init__('ggl:shared/vault:Vault', name, None, opts)

        config = pulumi.Config("gcp")
        region = config.require("region")
        zone = config.require("zone")
        project = config.require("project")

        # Set Vault DNS CNAME to `ghs.googlehosted.com.`
        env_dns_zone = gcp.dns.get_managed_zone(
            name=self.dns_zone)
        
        dns = gcp.dns.RecordSet(
            resource_name=name,
            name=f"{self.subdomain}.{env_dns_zone.dns_name}",
            type="CNAME",
            ttl=300,
            managed_zone=env_dns_zone.name,
            rrdatas=["ghs.googlehosted.com."],
            opts=pulumi.ResourceOptions(parent=self))

        # New kms KeyRing and key
        keyring = gcp.kms.KeyRing(
            resource_name=name,
            location=region,
            opts=pulumi.ResourceOptions(parent=self))
        key = gcp.kms.CryptoKey(
            resource_name=name,
            key_ring=keyring.id,
            rotation_period=f"{30*DAYS}s",
            destroy_scheduled_duration=f"{2*DAYS}s",
            opts=pulumi.ResourceOptions(parent=self))

        # New service account
        service_account_id = random.RandomId(
            resource_name=name,
            byte_length=6,
            opts=pulumi.ResourceOptions(parent=self))
        
        service_account = gcp.serviceaccount.Account(
            resource_name=name,
            account_id=service_account_id.hex.apply(lambda id: f"{name}-{id}"),
            opts=pulumi.ResourceOptions(parent=self))
        
        sa_email_foramatted = service_account.email.apply(lambda email: f"serviceAccount:{email}")

        # Set SA permissions
        gcp.projects.iam_member.IAMMember(
            resource_name=name,
            member=sa_email_foramatted,
            role="roles/storage.objectAdmin",
            project=project,
            opts=pulumi.ResourceOptions(parent=self))
        
        gcp.kms.KeyRingIAMMember(
            resource_name=name,
            member=sa_email_foramatted,
            role="roles/owner",
            key_ring_id=keyring.id,
            opts=pulumi.ResourceOptions(parent=self))

        # New bucket
        storage_bucket = gcp.storage.Bucket(
            resource_name=name,
            location="US",
            public_access_prevention="enforced",
            force_destroy=True,
            opts=pulumi.ResourceOptions(parent=self))

        # Generate config
        config_template = """ui = true
storage "gcs" {{
    bucket = "{}"
}}

listener "tcp" {{
    address       = "0.0.0.0:8200"
    tls_disable   = true
}}

seal "gcpckms" {{
    project     = "{}"
    region      = "{}"
    key_ring    = "{}"
    crypto_key  = "{}"
}}
""".replace("    ", "\t")
        
        config = pulumi.Output.all(
            bucket_name=storage_bucket.name,
            project=project,
            region=region,
            key_ring=keyring.name,
            crypto_key=key.name).apply(
                lambda args: config_template.format(args["bucket_name"], args["project"], args["region"], args["key_ring"], args["crypto_key"]))


        # Create cloud run service
        cloudrun_service = gcp.cloudrunv2.Service(
            resource_name=name,
            location=region,
            template={
                "containers": [{
                    "image": VAULT_IMAGE,
                    "resources": {
                        "limits": {
                            "cpu": "1",
                            "memory": "512Mi"
                        }
                    },
                    "ports": {
                        "container_port": 8200
                    },
                    "args": ["server"],
                    "envs": [{
                        "name": "SKIP_SETCAP",
                        "value":"true"
                    },{
                        "name": "VAULT_LOCAL_CONFIG",
                        "value": config
                    }]
                }],
                "annotations": {
                    "run.googleapis.com/cpu-throttling": "false"
                },
                "service_account": service_account.email
            },
            opts=pulumi.ResourceOptions(parent=self))

        # Allow all users to access cloud run service
        gcp.cloudrunv2.ServiceIamMember(
            resource_name=name,
            name=cloudrun_service.name,
            location=region,
            role="roles/run.invoker",
            member="allUsers",
            opts=pulumi.ResourceOptions(parent=self))

        # Domain mapping for vault
        gcp.cloudrun.DomainMapping(
            resource_name=name,
            location=region,
            name=dns.name.apply(lambda domain: domain.removesuffix(".")),
            metadata={
                "namespace": project,
            },
            spec={
                "route_name": cloudrun_service.name
            })

        # Use private domain and custom curl to init vault
        init_output = pulumi.Output.all(cloudrun_service.uri).apply(
            lambda uri: self.init(uri[0])
        )

        # Store public url, and root_token
        self.public_url = dns.name.apply(lambda domain: f"https://{domain.removesuffix('.')}")
        self.private_url = cloudrun_service.uri
        self.root_token = init_output.apply(lambda res: res["root_token"])

        return

    def init(self, uri: str):
        init_payload = """{
    "recovery_shares": 5,
    "recovery_threshold": 3,
    "stored_shares": 5
}"""

        cmd_res = local.Command(
            resource_name=self.name,
            create=f"curl -s -X POST --data '{init_payload}' {uri}/v1/sys/init",
            opts=pulumi.ResourceOptions(parent=self))
        
        def err_check(stderr: str):
            if len(stderr) > 0:
                pulumi.export("error", f"vault init failed: {stderr}")
                raise Exception(f"Failed to init vault server {uri}")
        
        stderr = cmd_res.stderr.apply(
            lambda stderr: err_check(stderr)
        )

        init_output = cmd_res.stdout.apply(
            lambda stdout: json.loads(stdout)
        )

        return init_output


    @property
    def name(self):
        return self.__name
    
    @name.setter
    def name(self, value: str):
        regex = r"[a-z0-9-]+"
        assert re.fullmatch(regex, value) is not None, f"name must match {regex}"
        self.__name = value

    @property
    def subdomain(self):
        return self.__subdomain
    
    @subdomain.setter
    def subdomain(self, value: str):
        regex = r"[a-z0-9-]+"
        assert re.fullmatch(regex, value) is not None, f"subdomain must match {regex}"
        self.__subdomain = value

    @property
    def dns_zone(self):
        return self.__dns_zone
    
    @dns_zone.setter
    def dns_zone(self, value: str):
        regex = r"[a-z0-9]+-[a-z]+"
        assert re.fullmatch(regex, value) is not None, f"GCP dns_zone must match {regex}"
        self.__dns_zone = value