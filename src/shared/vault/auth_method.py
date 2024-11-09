import json
from typing import List
import pulumi
import pulumi_vault as pvault
import re

class AuthMethodJWT(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                path: str,
                desc: str,
                discover_url: str,
                provider_config: dict,
                oidc_scopes: List[str],
                claim_mappings: dict,
                opts = None):

        super().__init__('ggl:shared/vault:AuthMethodJWT', name, None, opts)

        # Set and validate vars from constructor
        self.name = name
        self.path = path

        # Set and validate vars from config
        vault_config = pulumi.Config("vault")
        self.vault_address = vault_config.require("address")

        config = pulumi.Config("ggl")
        client_id = config.require("client_id")
        client_secret = config.require("client_secret")

        # Setup vault google auth method
        oidc_default_role = "user"
        google_auth_method = pvault.jwt.AuthBackend(
            resource_name=name,
            description=desc,
            oidc_discovery_url=discover_url,
            path=self.path,
            type="oidc",
            default_role=oidc_default_role,
            oidc_client_id=client_id,
            oidc_client_secret=client_secret,
            provider_config=provider_config,
            opts=pulumi.ResourceOptions(parent=self))

        self.oidc_redirect_uri = f"{self.vault_address}/ui/vault/auth/{self.path}/oidc/callback"
        pvault.jwt.AuthBackendRole(
            resource_name=name,
            backend=google_auth_method.path,
            user_claim="email",
            groups_claim="groups",
            role_name=oidc_default_role,
            token_policies=["default"],
            oidc_scopes=oidc_scopes,
            allowed_redirect_uris=[
                self.oidc_redirect_uri,
                "http://localhost:8250/oidc/callback",
            ],
            claim_mappings=claim_mappings,
            opts=pulumi.ResourceOptions(parent=self))
        
        self.auth_accessor = google_auth_method.accessor

        # https://developer.hashicorp.com/vault/docs/auth/jwt/oidc-providers/google
        # Go to console.cloud.google.com
        # IAM & Admin > Service accounts > vault-core-... > Advanced Settings > Domain-wide delegation
        # Copy the client ID `108356764425394966944`
        # Click "View google workspace admin console"
        # ... > Security > Access and data control > API controls > Domain wide delegation > Add new
        # Paste ID
        # Paste scopes: `https://www.googleapis.com/auth/admin.directory.group.readonly https://www.googleapis.com/auth/admin.directory.user.readonly`
        # Generate service account credentials save them store them to config secret

        # https://developer.hashicorp.com/vault/tutorials/auth-methods/identity#create-an-external-group

        lab_admins = pvault.identity.Group(
           resource_name=name,
            name="labadmins@hul.to",
            type="external",
            policies=[
                "admin",
                "default",
            ],
            metadata={
                "organization": "Lab administrators",
            },
            opts=pulumi.ResourceOptions(parent=self))

        group_alias = pvault.identity.GroupAlias(
            resource_name=f"{name}-alias",
            name="labadmins@hul.to",
            mount_accessor=google_auth_method.accessor,
            canonical_id=lab_admins.id,
            opts=pulumi.ResourceOptions(parent=self))


    @property
    def name(self):
        return self.__name
    
    @name.setter
    def name(self, value: str):
        regex = r"[a-z0-9-]+"
        assert re.fullmatch(regex, value) is not None, f"name must match {regex}"
        self.__name = value

    @property
    def path(self):
        return self.__path
    
    @path.setter
    def path(self, value: str):
        regex = r"[a-z0-9-]+"
        assert re.fullmatch(regex, value) is not None, f"path must match {regex}"
        self.__path = value

    @property
    def vault_address(self):
        return self.__vault_address
    
    @vault_address.setter
    def vault_address(self, value: str):
        regex = r"https:\/\/[a-z0-9-.]+"
        assert re.fullmatch(regex, value) is not None, f"vault_address {value} must match {regex}"
        self.__vault_address = value

