package vault

import (
	"github.com/pulumi/pulumi-vault/sdk/v6/go/vault"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

type KeyValueSecrets struct {
	MountName string
}

func (v HashicorpVault) NewKv(ctx *pulumi.Context, name string, desc string) (*vault.Mount, error) {
	mount, err := vault.NewMount(ctx, name, &vault.MountArgs{
		Path: pulumi.String(name),
		Type: pulumi.String("kv-v2"),
		Options: pulumi.Map{
			"version": pulumi.Any("2"),
			"type":    pulumi.Any("kv-v2"),
		},
		Description: pulumi.String(desc),
	})
	if err != nil {
		return &vault.Mount{}, err
	}
	return mount, nil

}
