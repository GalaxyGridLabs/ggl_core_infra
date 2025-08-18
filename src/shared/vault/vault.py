import json
import pulumi
import pulumi_gcp as gcp
import pulumi_random as prandom
from pulumi_command import local
import re

from ..constants import DAYS

VAULT_IMAGE = "docker.io/hashicorp/vault:1.20.0@sha256:5cd2003247e0a574a66c66aee1916b1e9e7f99640298f2e61271a8842d2d2a19"
VAULT_PORT = 8200
VAULT_MACHINE_TYPE = "f1-micro"

CADDY_IMAGE = "docker.io/library/caddy:2.9-alpine@sha256:9cc41f26f734861421d99f00fc962b3a3181aab9b4dbd0ac7751a883623794b6"
CADDY_HTTPS_PORT = 443
CADDY_HTTP_PORT = 80
COS_IMAGE = "projects/cos-cloud/global/images/cos-stable-113-18244-151-9"
COS_DISK_SIZE = 10


class Vault(pulumi.ComponentResource):
    def __init__(self, name: str, subdomain: str, dns_zone: str, opts=None):

        # Set and validate inputs
        self.name = name
        self.subdomain = subdomain
        self.dns_zone = dns_zone
        super().__init__("ggl:shared/vault:Vault", name, None, opts)

        config = pulumi.Config("gcp")
        region = config.require("region")
        zone = config.require("zone")
        project = config.require("project")

        env_dns_zone = gcp.dns.get_managed_zone(name=self.dns_zone)

        fqdn = f"{self.subdomain}.{env_dns_zone.dns_name}".removesuffix(".")

        # New kms KeyRing and key
        keyring = gcp.kms.KeyRing(
            resource_name=name,
            location=region,
            opts=pulumi.ResourceOptions(parent=self),
        )
        key = gcp.kms.CryptoKey(
            resource_name=name,
            key_ring=keyring.id,
            rotation_period=f"{30*DAYS}s",
            destroy_scheduled_duration=f"{2*DAYS}s",
            opts=pulumi.ResourceOptions(parent=self),
        )

        # New service account
        service_account_id = prandom.RandomId(
            resource_name=f"sa{name}",
            byte_length=6,
            opts=pulumi.ResourceOptions(parent=self),
        )

        service_account = gcp.serviceaccount.Account(
            resource_name=name,
            account_id=service_account_id.hex.apply(lambda id: f"{name}-{id}"),
            opts=pulumi.ResourceOptions(parent=self),
        )

        sa_email_foramatted = service_account.email.apply(
            lambda email: f"serviceAccount:{email}"
        )

        # Set SA permissions
        gcp.projects.iam_member.IAMMember(
            resource_name=name,
            member=sa_email_foramatted,
            role="roles/storage.objectAdmin",
            project=project,
            opts=pulumi.ResourceOptions(parent=self),
        )

        gcp.kms.KeyRingIAMMember(
            resource_name=name,
            member=sa_email_foramatted,
            role="roles/owner",
            key_ring_id=keyring.id,
            opts=pulumi.ResourceOptions(parent=self),
        )

        # New bucket
        storage_bucket = gcp.storage.Bucket(
            resource_name=name,
            location="US",
            public_access_prevention="enforced",
            force_destroy=True,
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Generate config
        config_template = """ui = true
disable_mlock = true

storage "gcs" {{
    bucket = "{}"
}}

listener "tcp" {{
    address       = "0.0.0.0:{}"
    tls_disable   = true
}}

seal "gcpckms" {{
    project     = "{}"
    region      = "{}"
    key_ring    = "{}"
    crypto_key  = "{}"
}}
""".replace(
            "    ", "\t"
        )

        config = pulumi.Output.all(
            bucket_name=storage_bucket.name,
            project=project,
            region=region,
            key_ring=keyring.name,
            vault_port=VAULT_PORT,
            crypto_key=key.name,
        ).apply(
            lambda args: config_template.format(
                args["bucket_name"],
                args["vault_port"],
                args["project"],
                args["region"],
                args["key_ring"],
                args["crypto_key"],
            )
        )

        # Setup FW rules
        vault_tag = prandom.RandomId(
            resource_name=f"fw{name}",
            prefix=f"{name}-",
            byte_length=3,
            opts=pulumi.ResourceOptions(parent=self),
        )
        vault_fw = gcp.compute.Firewall(
            resource_name=name,
            network="default",
            allows=[
                {
                    "protocol": "tcp",
                    "ports": [
                        CADDY_HTTPS_PORT,
                        CADDY_HTTP_PORT,
                    ],
                },
            ],
            target_tags=[vault_tag.hex],
            source_ranges=["0.0.0.0/0"],
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Setup Caddy https reverse proxy 443 -TLS-> 3000
        user_data = f"""#cloud-config

write_files:
- path: /etc/systemd/system/caddy.service
  owner: root:root
  permissions: '0755'
  content: |
      [Unit]
      Description=Startup caddy container
      Requires=docker.service
      After=docker.service

      [Service]
      Type=simple
      ExecStart=/usr/bin/docker run -p 443:{CADDY_HTTPS_PORT} -p 80:{CADDY_HTTP_PORT} -v /var/caddy/:/data:rw --add-host=host.docker.internal:host-gateway --name caddy {CADDY_IMAGE} caddy run --config /data/Caddyfile --adapter caddyfile
      Restart=always
      RestartSec=30

      [Install]
      WantedBy=multi-user.target
- path: /var/caddy/Caddyfile
  owner: root:root
  permissions: '0755'
  content: |
      {fqdn} {{
        reverse_proxy host.docker.internal:{VAULT_PORT}
      }}
runcmd:
  - systemctl daemon-reload
  - systemctl enable --now caddy
"""

        # Create a COS spec
        def generate_spec(config: str):
            config = config.replace("\n", "\n        ")
            return f"""
spec:
  containers:
  - name: {name}
    image: {VAULT_IMAGE}
    args: ["server"]
    env:
    - name: SKIP_SETCAP
      value: 'true'
    - name: VAULT_LOCAL_CONFIG
      value: |
        {config}
    stdin: false
    tty: false
"""

        spec_str = pulumi.Output.all(config=config).apply(
            lambda args: generate_spec(args["config"])
        )

        # Deploy COS instance
        cos_instance = gcp.compute.Instance(
            resource_name=name,
            machine_type=VAULT_MACHINE_TYPE,
            boot_disk={
                "initialize_params": {
                    "image": COS_IMAGE,
                    "size": COS_DISK_SIZE,
                    "type": "pd-standard",
                }
            },
            tags=[vault_tag.hex],
            network_interfaces=[
                {
                    "access_configs": [
                        {
                            "nat_ip": "",
                            "network_tier": "STANDARD",
                        }
                    ],
                    "subnetwork": "default",
                    "stack_type": "IPV4_ONLY",
                }
            ],
            service_account={
                "email": service_account.email,
                "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
            },
            allow_stopping_for_update=True,
            metadata={
                "gce-container-declaration": spec_str,
                "google-logging-enabled": True,
                "user-data": user_data,
            },
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
                replace_on_changes=["metadata"],
            ),
        )

        self.ip_addr = cos_instance.network_interfaces[0].apply(
            lambda iface: iface.access_configs[0].nat_ip
        )

        dns = gcp.dns.RecordSet(
            resource_name=name,
            name=f"{self.subdomain}.{env_dns_zone.dns_name}",
            type="A",
            ttl=300,
            managed_zone=env_dns_zone.name,
            rrdatas=[self.ip_addr],
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.url = dns.name.apply(lambda domain: f"https://{domain.removesuffix('.')}/")

        """
        Configure Domain Wide Delegation for the vault Service Account.
        https://developers.google.com/workspace/guides/create-credentials#optional_set_up_domain-wide_delegation_for_a_service_account

        Copy the client ID and navigate to the API Controls.

        Grant the following OAuth scopes to the service account:

        https://www.googleapis.com/auth/admin.directory.group.readonly
        https://www.googleapis.com/auth/admin.directory.user.readonly
        """

    def init(self, uri: str):
        init_payload = """{
    "recovery_shares": 5,
    "recovery_threshold": 3,
    "stored_shares": 5
}"""

        cmd_res = local.Command(
            resource_name=self.name,
            create=f"curl -s -X POST --data '{init_payload}' {uri}/v1/sys/init",
            opts=pulumi.ResourceOptions(parent=self),
        )

        def err_check(stderr: str):
            if len(stderr) > 0:
                pulumi.export("error", f"vault init failed: {stderr}")
                raise Exception(f"Failed to init vault server {uri}")

        stderr = cmd_res.stderr.apply(lambda stderr: err_check(stderr))

        init_output = cmd_res.stdout.apply(lambda stdout: json.loads(stdout))

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
        assert (
            re.fullmatch(regex, value) is not None
        ), f"GCP dns_zone must match {regex}"
        self.__dns_zone = value
