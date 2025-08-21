"""A Python Pulumi program"""

import json
import os
import pulumi
import pulumi_vault as pvault

from shared.vault.auth_method import AuthMethodJWT
from shared.vault.oidc_provider import OIDCProvider
from shared.git.git import Gitea
from shared.vault.group_external import GroupExternal
from shared.vault.ssh_ca import SSHCertificateAuthority, SSHCertificateAuthorityRole
from shared.vault.pki import PKI


def main():
    print("Starting")

    # Create vault policies
    policies_dir = "../shared/vault/policies"
    for policy_file in os.listdir(policies_dir):
        with open(f"{policies_dir}/{policy_file}", "r") as f:
            name = policy_file.removesuffix(".hcl")
            pvault.Policy(resource_name=f"policy-{name}", name=name, policy=f.read())

    config = pulumi.Config("ggl")
    sa_secret = config.require("vault_sa_account_json")
    sa_email = json.loads(sa_secret)["client_email"]
    gsuite_admin = config.require("gsuite_admin")
    gsuite_domain = config.require("gsuite_domain")

    # Setup vault google auth method
    google_auth = AuthMethodJWT(
        name="google-auth",
        path="oidc",
        desc="Authenticate to lab using GSuite account",
        discover_url="https://accounts.google.com",
        oidc_scopes=["openid", "email", "profile"],
        provider_config={
            "provider": "gsuite",
            "gsuite_service_account": sa_secret,
            "gsuite_admin_impersonate": gsuite_admin,
            "fetch_groups": True,
            "domain": gsuite_domain,
            "fetch_user_info": True,
            "groups_recurse_max_depth": 5,
            "impersonate_principal": sa_email,
        },
        claim_mappings={
            "email": "email",
            "groups": "groups",
            "given_name": "nickname",
        },
        user_claim="email",
    )

    # Setup vault oidc provider for gitea
    def gen_accessor_template(accessor: str):
        return f"""{{
    "username":{{{{identity.entity.aliases.{accessor}.name}}}},
    "groups": {{{{identity.entity.groups.names}}}},
    "email": {{{{identity.entity.aliases.{accessor}.metadata.email}}}},
    "nickname": {{{{identity.entity.aliases.{accessor}.metadata.nickname}}}}
}}"""

    gitea_oidc = OIDCProvider(
        name="gitea-auth",
        redirect_uris=["https://git.galaxygridlabs.com/user/oauth2/vault/callback"],
        scope_template=google_auth.auth_accessor.apply(
            lambda accessor: gen_accessor_template(accessor)
        ),
    )
    pulumi.export("git_client_id", gitea_oidc.client_id)
    pulumi.export("git_client_secret", gitea_oidc.client_secret)

    # Setup labadmins group
    lab_admins = GroupExternal(
        name="labadmins",
        group_name="labadmins@hul.to",
        policies=["admin", "default"],
        metadata={"organization": "Lab administrators"},
        auth_mount_accessor=google_auth.auth_accessor,
    )

    lab_users = GroupExternal(
        name="labusers",
        group_name="labusers@hul.to",
        policies=["default"],
        metadata={"organization": "Lab users"},
        auth_mount_accessor=google_auth.auth_accessor,
    )

    red_team = GroupExternal(
        name="redteam",
        group_name="red-team@hul.to",
        policies=["default"],
        metadata={"organization": "Red teamers"},
        auth_mount_accessor=google_auth.auth_accessor,
    )

    spellshift = GroupExternal(
        name="spellshift",
        group_name="spellshift@hul.to",
        policies=["default"],
        metadata={"organization": "Spellshift team"},
        auth_mount_accessor=google_auth.auth_accessor,
    )

    # Setup SSH CA
    lab_ca = SSHCertificateAuthority(name="lab-ssh")

    sysadmin_role = SSHCertificateAuthorityRole(
        name="lab-ssh-sysadmin", allowed_users=["sysadmin"], ssh_ca=lab_ca
    )
    user_role = SSHCertificateAuthorityRole(
        name="lab-ssh-user", allowed_users=["user"], ssh_ca=lab_ca
    )

    pulumi.export("ca_pubkey", lab_ca.public_key)

    # Setup PKI
    pki = PKI(name="pki")

    # New gitea server
    gitea = Gitea(name="gitea", subdomain="git", dns_zone="galaxygridlabs-com")

    pulumi.export("gitea", gitea.url)

    # Cloudflare OIDC provider
    cloudflare_oidc = OIDCProvider(
        name="cloudflare",
        redirect_uris=["https://hulto.cloudflareaccess.com/cdn-cgi/access/callback"],
        scope_template=google_auth.auth_accessor.apply(
            lambda accessor: gen_accessor_template(accessor)
        ),
    )

    harvester_cert = pki.create_cert(
        name="harvester", domain="harvester.internal.galaxygridlabs.com"
    )

    rancher_cert = pki.create_cert(
        name="rancher", domain="rancher.internal.galaxygridlabs.com"
    )

    synology_cert = pki.create_cert(
        name="synology", domain="files.internal.galaxygridlabs.com"
    )

    openwebui_oidc = OIDCProvider(
        name="openwebui",
        redirect_uris=["https://ollama.astral-labs.work/oauth/oidc/callback"],
        scope_template=google_auth.auth_accessor.apply(
            lambda accessor: gen_accessor_template(accessor)
        ),
    )
    pulumi.export("openwebui_oidc_client_id", openwebui_oidc.client_id)
    pulumi.export("openwebui_oidc_client_secret", openwebui_oidc.client_secret)


if __name__ == "__main__":
    main()
