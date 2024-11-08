"""A Python Pulumi program"""

import os
import pulumi
import pulumi_vault as pvault

from shared.vault.auth_method import AuthMethodJWT
from shared.vault.oidc_provider import OIDCProvider
from shared.git.git import Gitea

def main():
    print("Starting")

    # Create vault policies
    policies_dir = "../shared/vault/policies"
    for policy_file in os.listdir(policies_dir):
        with open(f"{policies_dir}/{policy_file}", 'r') as f:
            name = policy_file.removesuffix(".hcl")
            pvault.Policy(
                resource_name=f"policy-{name}",
                name=name,
                policy=f.read())

    # Setup vault google auth method
    google_auth = AuthMethodJWT(
        name="google-auth",
        path="oidc",
        desc="Authenticate to lab using GSuite account",
        discover_url="https://accounts.google.com")

    # Setup vault oidc provider for gitea
    gitea_oidc = OIDCProvider(
        name="gitea-auth",
        redirect_uris=["http://localhost:3000/user/oauth2/vault/callback"])

    pulumi.export("client_id", gitea_oidc.client_id)
    pulumi.export("client_secret", gitea_oidc.client_secret)

    # New gitea server
    gitea = Gitea(
        name="gitea",
        subdomain="git",
        dns_zone="galaxygridlabs-com")


if __name__ == "__main__":
    main()