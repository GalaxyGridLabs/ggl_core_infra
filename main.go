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

		vault, err := vault.NewVault(ctx, project, region, "main")
		if err != nil {
			return err
		}

		ctx.Export("token", vault["root_token"])
		ctx.Export("url", vault["url"])

		return nil
	})
}
