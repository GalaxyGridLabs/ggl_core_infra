package main

import (
	"ggl_core_infra/internal/vault"

	"github.com/pulumi/pulumi-random/sdk/v4/go/random"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

const randIdLength = 6

func randomId(ctx *pulumi.Context, name string) (pulumi.StringOutput, error) {
	// Create service account for vault
	vaultSvcAccNameHex, err := random.NewRandomId(ctx, name, &random.RandomIdArgs{
		ByteLength: pulumi.Int(randIdLength),
	})
	if err != nil {
		return pulumi.StringOutput{}, err
	}

	return vaultSvcAccNameHex.Hex, nil
}

func main() {
	pulumi.Run(func(ctx *pulumi.Context) error {

		project := "galaxygridlabs"
		region := "us-central1"

		r1, err := randomId(ctx, "test1")
		if err != nil {
			return err
		}
		r1.ApplyT(func(id string) (*vault.HashicorpVault, error) {
			vault, err := vault.NewVault(ctx, project, region, id)
			if err != nil {
				return nil, err
			}
			return vault, nil
		})

		r2, err := randomId(ctx, "test2")
		if err != nil {
			return err
		}
		r2.ApplyT(func(id string) (*vault.HashicorpVault, error) {
			vault, err := vault.NewVault(ctx, project, region, id)
			if err != nil {
				return nil, err
			}
			return vault, nil
		})

		// vault, err := vault.NewVault(ctx, project, region, "test")
		// if err != nil {
		// 	return err
		// }

		// ctx.Export("url", vault.Url)

		return nil
	})
}
