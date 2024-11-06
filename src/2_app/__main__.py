"""A Python Pulumi program"""

import pulumi
import pulumi_vault as pvault

from shared.vault.auth_method import AuthMethodJWT
from shared.vault.oidc_provider import OIDCProvider
from shared.git.git import Gitea

def main():
    print("Starting")

    # Setup vault google auth method
    google_auth = AuthMethodJWT(
        name="google-auth",
        path="oidc",
        desc="Authenticate to lab using GSuite account",
        discover_url="https://accounts.google.com")

    # Setup vault oidc provider for gitea
    gitea_oidc = OIDCProvider(
        name="gitea-auth",
        redirect_uris=["https://git.galaxygridlabs.com/oidc/callback"])

    pulumi.export("client_id", gitea_oidc.client_id)
    pulumi.export("client_secret", gitea_oidc.client_secret)

    # New gitea server
    gitea = Gitea(
        name="gitea",
        subdomain="git",
        dns_zone="galaxygridlabs-com")


if __name__ == "__main__":
    main()