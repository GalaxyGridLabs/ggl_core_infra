package vault

import (
	"github.com/pulumi/pulumi-vault/sdk/v6/go/vault"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

type AuthOidc struct {
	MountName string
}

func (v *HashicorpVault) NewAuthOidc(ctx *pulumi.Context, name string, desc string) (*vault.Mount, error) {

	/**
	# Create the OIDC auth mechanism using default policy

	$ vault auth enable oidc

	$ vault write auth/oidc/config \
	  	oidc_discovery_url="https://accounts.google.com" \
		oidc_client_id="$OAUTH_CLIENT_ID" \
		oidc_client_secret="$OAUTH_CLIENT_SECRET" \
		default_role="default-user"

	$ vault write auth/oidc/role/default-user \
		user_claim="sub" \
		bound_audiences=$OAUTH_CLIENT_ID \
		allowed_redirect_uris="$VAULT_ADDR/ui/vault/auth/oidc/oidc/callback" \
		policies=default \
		ttl=1h

	$

	# Create jack entity

	$ vault write identity/entity name="hulto" policies="admin"
	id         5da0c07d-3f76-d4b4-20c8-88a44f42f213

	# Create admin policy
	$ vault policy write admin ./internal/vault/policies/admin.hcl

	# Grant admin to hulto@hul.to

	// $ vault write identity/group name="admin" policies="admin" member_entity_ids=5da0c07d-3f76-d4b4-20c8-88a44f42f213

	# Automatically associate hulto and hulto@hul.to - probably can't do automatically. Need user to auth, grab their sub-id and then create alias mapping.

	$ vault

	$ vault write identity/entity-alias name="hulto-oidc" \
		canonical_id=5da0c07d-3f76-d4b4-20c8-88a44f42f213 \
		mount_accessor=auth_oidc_ee34c862

	**/

	// mount, err := vault.NewMount(ctx, name, &vault.MountArgs{
	// 	Path: pulumi.String(name),
	// 	Type: pulumi.String("kv-v2"),
	// 	Options: pulumi.Map{
	// 		"version": pulumi.Any("2"),
	// 		"type":    pulumi.Any("kv-v2"),
	// 	},
	// 	Description: pulumi.String(desc),
	// }, pulumi.Parent(v))
	// if err != nil {
	// 	return &vault.Mount{}, err
	// }
	// return mount, nil

	return nil, nil
}
