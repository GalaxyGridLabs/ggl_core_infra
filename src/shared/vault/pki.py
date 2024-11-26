import pulumi
import re
import pulumi_vault as vault
from ..constants import YEARS

MAX_TTL = 2*YEARS

class PKI(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                opts = None):

        super().__init__('ggl:shared/vault:PKI', name, None, opts)

        mount = vault.mount.Mount(
            resource_name=name,
            path=name,
            type="pki",
            max_lease_ttl_seconds=MAX_TTL,
            opts=pulumi.ResourceOptions(parent=self))
        
        self.mount = mount

        root_cert = vault.pkisecret.SecretBackendRootCert(
            resource_name=name,
            backend=mount.path,
            type="internal",
            ttl=MAX_TTL,
            format="pem",
            common_name="Root CA",
            ou="Galaxy Grid",
            organization="Labs",
            exclude_cn_from_sans=True,
            opts=pulumi.ResourceOptions(parent=self))
        
        vault_config = pulumi.Config("vault")
        self.vault_address = vault_config.require("address")

        vault.pkisecret.SecretBackendConfigUrls(
            resource_name=name,
            backend=mount.path,
            crl_distribution_points=[f"{self.vault_address}/v1/{name}/ca"],
            issuing_certificates=[f"{self.vault_address}/v1/{name}/crl"],
            opts=pulumi.ResourceOptions(parent=self))
    
    def create_cert(
            self,
            name: str,
            domain: str):
        
        # Extract the domain without subdomains
        m = re.search(r"([a-zA-Z0-9-]+)(\.[a-zA-Z]{2,5})?(\.[a-zA-Z]+$)", domain)
        assert m is not None, f"could not extract domain from {domain}"
        lab_domain = "".join([g for g in m.groups() if g is not None])
        
        role = vault.pkisecret.SecretBackendRole(
            resource_name=name,
            name=name,
            backend=self.mount.path,
            ttl=MAX_TTL,
            allowed_domains=[lab_domain],
            allow_subdomains=True,
            opts=pulumi.ResourceOptions(parent=self))

        certificate = vault.pkisecret.SecretBackendCert(
            resource_name=name,
            name=role.name,
            common_name=domain,
            backend=self.mount.path,
            ttl=1*YEARS,
            opts=pulumi.ResourceOptions(parent=self))

        return certificate.certificate, certificate.private_key