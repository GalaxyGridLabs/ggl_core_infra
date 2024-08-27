package main

import (
	"ggl_core_infra/internal/git"
	"ggl_core_infra/internal/vault"
	"log"

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

		// _, err := common.NewNetwork(ctx, "lab-net", project, region, "main")
		// if err != nil {
		// 	return err
		// }

		vaultMain, err := vault.NewVault(ctx, project, region, "main")
		if err != nil {
			return err
		}

		gitMain, err := git.NewGitea(ctx, project, region, "main")
		if err != nil {
			return err
		}

		ctx.Export("git_url", gitMain.MapOutput["url"])

		// Stage 2
		vaultMain.MapOutput.ToMapOutput().ApplyT(func(t map[string]interface{}) error {
			log.Printf("token: %s\n", t["root_token"])
			log.Printf("url: %s\n", t["url"])

			log.Printf(`Set your vault address and token:
pulumi config set vault:address %s
pulumi config set vault:token %s --secret
`, t["url"].(string), t["root_token"].(string))

			// _, err := vaultMain.NewKv(ctx, "admin/core/example", "A Test KV")
			// if err != nil {
			// 	return err
			// }

			return nil
		})

		return nil
	})
}
