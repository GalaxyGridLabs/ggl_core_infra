resource "vault_jwt_auth_backend" "google-oidc" {
    description         = "Allow users to authenticate with google account"
    path                = "jwt"
    oidc_discovery_url  = "https://accounts.google.com"
    oidc_client_id      = "1051431507099-u73qbnpdm85ft4ies07bvsl96el91r9u.apps.googleusercontent.com"
    oidc_client_secret  = ""
    default_role        = "default"
}

resource "vault_jwt_auth_backend_role" "google-oidc" {
  backend               = vault_jwt_auth_backend.google-oidc.path
  role_name             = "default"
  token_policies        = [vault_policy.admin_policy["admin.hcl"].name]
  oidc_scopes           = ["openid", "profile", "email"]
  user_claim            = "email"
  role_type             = "oidc"
  allowed_redirect_uris = ["https://127.0.0.1:8200/ui/vault/auth/oidc/oidc/callback", "https://vault.galaxygridlabs.com/ui/vault/auth/oidc/oidc/callback"]
#   bound_claims          = { "email" : join(",", [var.email]) }
}
