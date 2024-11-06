"""A Python Pulumi program"""

import pulumi
import pulumi_vault as pvault

from shared.vault.auth_method import AuthMethodJWT

def main():
    print("Starting")

    # Setup vault google auth method
    google_auth = AuthMethodJWT("google-auth","oidc")

    # Setup vault oidc provider for gitea

    # New gitea server


if __name__ == "__main__":
    main()