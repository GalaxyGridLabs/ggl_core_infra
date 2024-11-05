"""A Google Cloud Python Pulumi program"""

import pulumi

from shared.vault.vault import Vault

def main():
    vault = Vault("vault", "galaxygridlabs-com")


if __name__ == "__main__":
    main()
