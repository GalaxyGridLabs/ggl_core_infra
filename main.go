package main

import (
	"ggl_core_infra/internal/vault"

	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

func main() {
	pulumi.Run(func(ctx *pulumi.Context) error {
		project := "galaxygridlabs"
		region := "us-central1"
		err := vault.NewVault(ctx, project, region)
		if err != nil {
			return err
		}
		return nil
	})
}
