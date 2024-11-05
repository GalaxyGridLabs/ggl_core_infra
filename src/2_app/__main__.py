"""A Python Pulumi program"""

import pulumi

def configure_vault():
    print("Configuring vault")
    # Configure Vault oauth2 auth method with google

    # Configur vault policies

def setup_gitea():
    print("Setting up gitea")
    # Setup vault oidc provider for gitea

    # Generate gitea config: oidc client-id, oidc secret, admin account, misc configs.

    # Deploy COS conatiner

def main():
    print("Starting")

if __name__ == "__main__":
    main()