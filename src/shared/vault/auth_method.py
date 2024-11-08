import pulumi
import pulumi_vault as pvault
import re

class AuthMethodJWT(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                path: str,
                desc: str,
                discover_url: str,
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
        sa_secret = config.require("vault_sa_account_json")


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
            provider_config={
                "provider": "gsuite",
                "gsuite_service_account": sa_secret,
                "gsuite_admin_impersonate": "hulto@hul.to",
                "fetch_groups": True,
                "domain": "hul.to",
                "fetch_user_info": True,
                "groups_recurse_max_depth": 5,
                "impersonate_principal": "vault-core-40809eee975c@galaxygridlabs.iam.gserviceaccount.com",
            },
            opts=pulumi.ResourceOptions(parent=self))

        self.oidc_redirect_uri = f"{self.vault_address}/ui/vault/auth/{self.path}/oidc/callback"
        pvault.jwt.AuthBackendRole(
            resource_name=name,
            backend=google_auth_method.path,
            user_claim="email",
            groups_claim="groups",
            role_name=oidc_default_role,
            token_policies=["default"],
            oidc_scopes=["openid","email"],
            allowed_redirect_uris=[
                self.oidc_redirect_uri,
                "http://localhost:8250/oidc/callback",
            ],
            claim_mappings={
                "email": "email",
                "picture": "pfp",
                "groups": "groups",
            },
            opts=pulumi.ResourceOptions(parent=self))

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
       
        #  hulto@saw  /tmp/test5 
        # $ vault write -format=json identity/group name="labadmins@hul.to" \
        #     policies="admin" \
        #     type="external" \
        #     metadata=organization="Lab administrators" | jq -r ".data.id" > group_id.txt


        #  hulto@saw  /tmp/test5 
        # $ cat group_id.txt 
        # ee87ad9c-5b71-1911-2ba9-4b28a794ce40

        #  hulto@saw  /tmp/test5 
        # $ vault write identity/group-alias name="labadmins@hul.to" \
        #     mount_accessor="auth_oidc_53f0016e" \
        #     canonical_id="ee87ad9c-5b71-1911-2ba9-4b28a794ce40"

        # Key             Value
        # ---             -----
        # canonical_id    ee87ad9c-5b71-1911-2ba9-4b28a794ce40
        # id              5f0a4040-5fee-abaf-687b-eab54f6aab69


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

