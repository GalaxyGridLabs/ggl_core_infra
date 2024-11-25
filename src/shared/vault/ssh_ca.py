from typing import List
import pulumi
import pulumi_vault as vault
from ..constants import MINUTES

class SSHCertificateAuthority(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                opts = None):

        super().__init__('ggl:shared/vault:SSHCertificateAuthority', name, None, opts)

        mount = vault.mount.Mount(
            resource_name=name,
            path=name,
            type="ssh",
            opts=pulumi.ResourceOptions(parent=self))

        self.mount_path = mount.path

        ca = vault.ssh.SecretBackendCa(
            resource_name=name,
            backend=self.mount_path,
            generate_signing_key=True,
            opts=pulumi.ResourceOptions(parent=self))
                
        self.public_key = ca.public_key


class SSHCertificateAuthorityRole(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                ssh_ca: SSHCertificateAuthority,
                allowed_users: List[str],
                opts = None):

        super().__init__('ggl:shared/vault:SSHCertificateAuthorityRole', name, None, opts=pulumi.ResourceOptions(parent=ssh_ca))

        role = vault.ssh.SecretBackendRole(
            resource_name=name,
            name=name,
            backend=ssh_ca.mount_path,
            key_type="ca",
            allow_user_certificates=True,
            allowed_users=",".join(allowed_users),
            max_ttl=60*MINUTES,
            ttl=60*MINUTES,
            opts=pulumi.ResourceOptions(parent=self))
