"""A Google Cloud Python Pulumi program"""

import pulumi

from shared.vault.vault import Vault

def main():
    vault = Vault("vault-core", "vault", "galaxygridlabs-com")
    pulumi.export("vault_root_token", vault.root_token)

if __name__ == "__main__":
    main()
