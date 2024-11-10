from typing import List
import pulumi
import pulumi_vault as pvault

import re
import json
from shared.constants import DAYS

class OIDCProvider(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                redirect_uris: List[str],
                scope_template: pulumi.Output,
                opts = None):

        super().__init__('ggl:shared/vault:OIDCProvider', name, None, opts)

        vault_config = pulumi.Config("vault")
        self.vault_address = vault_config.require("address")

        key = pvault.identity.OidcKey(
            resource_name=name,
            allowed_client_ids=["*"],
            rotation_period=1*DAYS,
            verification_ttl=1*DAYS,
            opts=pulumi.ResourceOptions(parent=self))

        client = pvault.identity.OidcClient(
            resource_name=name,
            name=name,
            key=key.name,
            redirect_uris=redirect_uris,
            assignments=["allow_all"],
            id_token_ttl=2400,
            access_token_ttl=7200,
            opts=pulumi.ResourceOptions(parent=self))

        scope = pvault.identity.OidcScope(
            resource_name=name,
            name=name,
            template=scope_template,
            description=f"Scope for the {name} oidc provider",
            opts=pulumi.ResourceOptions(parent=self))
        
        issuer_host = self.vault_address.split("://")[1]
        provider = pvault.identity.OidcProvider(
            resource_name=name,
            name=name,
            https_enabled=self.vault_address.startswith("https"),
            issuer_host=issuer_host,
            allowed_client_ids=[client.client_id],
            scopes_supporteds=[scope.name],
            opts=pulumi.ResourceOptions(parent=self))
        
        self.client_id = client.client_id
        self.client_secret = client.client_secret
        self.issuer_base = f"{self.vault_address}/v1/identity/oidc/provider/{provider.name}"

        return

    @property
    def vault_address(self):
        return self.__vault_address
    
    @vault_address.setter
    def vault_address(self, value: str):
        regex = r"https:\/\/[a-z0-9-.]+"
        assert re.fullmatch(regex, value) is not None, f"vault_address {value} must match {regex}"
        self.__vault_address = value