package vault

import (
	"github.com/pulumi/pulumi-vault/sdk/v6/go/vault/jwt"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

func (v *HashicorpVault) SetupOidcAuthBackend(ctx *pulumi.Context, name string, desc string, dnsName string, clientId string, clientSecret string) error {

	// 	# Create the OIDC auth mechanism using default policy

	// 	$ vault auth enable oidc

	oidcDefaultRole := "test-user"

	// 	$ vault write auth/oidc/config \
	// 	  	oidc_discovery_url="https://accounts.google.com" \
	// 		oidc_client_id="$OAUTH_CLIENT_ID" \
	// 		oidc_client_secret="$OAUTH_CLIENT_SECRET" \
	// 		default_role="default-user"
	googleAuth, err := jwt.NewAuthBackend(ctx, name, &jwt.AuthBackendArgs{
		Description:      pulumi.String(desc),
		OidcDiscoveryUrl: pulumi.String("https://accounts.google.com"),
		Path:             pulumi.String(name),
		Type:             pulumi.String("oidc"),
		DefaultRole:      pulumi.String(oidcDefaultRole),
		ProviderConfig:   pulumi.StringMap{
			// "provider":                 pulumi.String("gsuite"),
			// "fetch_groups":             pulumi.String("true"),
			// "fetch_user_info":          pulumi.String("true"),
			// "groups_recurse_max_depth": pulumi.String("1"),
		},
		OidcClientId:     pulumi.String(clientId),
		OidcClientSecret: pulumi.String(clientSecret),
	})
	if err != nil {
		return err
	}

	// $ vault write auth/oidc/role/default-user \
	// 		user_claim="sub" \
	// 		bound_audiences=$OAUTH_CLIENT_ID \
	// 		allowed_redirect_uris="$VAULT_ADDR/ui/vault/auth/oidc/oidc/callback" \
	// 		policies=default \
	// 		ttl=1h
	_, err = jwt.NewAuthBackendRole(ctx, oidcDefaultRole+"-role", &jwt.AuthBackendRoleArgs{
		Backend:   googleAuth.Path,
		UserClaim: pulumi.String("sub"),
		RoleName:  pulumi.String(oidcDefaultRole),
		TokenPolicies: pulumi.StringArray{
			pulumi.String("default"),
		},
		AllowedRedirectUris: pulumi.StringArray{
			pulumi.String("https://" + dnsName + "/ui/vault/auth/" + name + "/oidc/callback"),
		},
	})
	if err != nil {
		return err
	}

	// 	# Create jack entity

	// 	$ vault write identity/entity name="hulto" policies="admin"
	// 	id         5da0c07d-3f76-d4b4-20c8-88a44f42f213

	// 	# Create admin policy
	// 	$ vault policy write admin ./internal/vault/policies/admin.hcl

	// 	# Grant admin to hulto@hul.to

	// 	// $ vault write identity/group name="admin" policies="admin" member_entity_ids=5da0c07d-3f76-d4b4-20c8-88a44f42f213

	// 	# Automatically associate hulto and hulto@hul.to - probably can't do automatically. Need user to auth, grab their sub-id and then create alias mapping.

	// 	$ vault

	// 	$ vault write identity/entity-alias name="hulto-oidc" \
	// 		canonical_id=5da0c07d-3f76-d4b4-20c8-88a44f42f213 \
	// 		mount_accessor=auth_oidc_ee34c862

	// 	# Set default provider in vault to: https://vault.galaxygridlabs.com/

	// 	# TODO: Assign git users to orgs based on their vault groups

	// https://vault.galaxygridlabs.com/ui/vault/identity/oidc/provider/default/authorize?client_id=wWOeykAzVxxRDJpQEGRVnuYtef0Au6HZ&redirect_uri=
	// 	http://git.galaxygridlabs.com:3000/user/oauth2/vault/callback

	return nil
}
