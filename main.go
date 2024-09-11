package main

import (
	"fmt"
	"ggl_core_infra/internal/common"
	"ggl_core_infra/internal/git"
	"ggl_core_infra/internal/vault"
	"log"
	"net/url"
	"strings"

	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/compute"
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

func setupVault(ctx *pulumi.Context, project string, region string, labZone string) (*vault.HashicorpVault, error) {
	vaultMain, err := vault.NewVault(ctx, project, region, "main")
	if err != nil {
		return nil, err
	}

	// TODO: add DNS mapping
	cloudRunDns := vaultMain.MapOutput["url"].(pulumi.StringInput).ToStringOutput().ApplyT(func(u string) string {
		parsed, _ := url.Parse(u)
		var res_host string
		if !strings.HasSuffix(parsed.Host, ".") {
			res_host = fmt.Sprintf("%s.", parsed.Host)
		} else {
			res_host = parsed.Host
		}
		return res_host
	}).(pulumi.StringInput)

	vaultCname, err := common.NewDnsRecord(ctx, "vault-dns", "vault2", labZone, "CNAME", cloudRunDns)
	if err != nil {
		return nil, err
	}

	ctx.Export("private_vault_url", vaultMain.MapOutput["url"])
	ctx.Export("public_vault_domain", pulumi.String(vaultCname.DnsName))

	return vaultMain, nil
}

func setupGitea(ctx *pulumi.Context, project string, region string, labZone string) (*git.Gitea, error) {
	gitMain, err := git.NewGitea(ctx, project, region, "main")
	if err != nil {
		return nil, err
	}

	tmp_arr := gitMain.MapOutput["url"].(compute.InstanceNetworkInterfaceArrayOutput)
	git_nat_ip := tmp_arr.Index(pulumi.Int(0)).AccessConfigs().Index(pulumi.Int(0)).NatIp()

	tmp := git_nat_ip.ApplyT(func(n *string) string {
		return *n
	}).(pulumi.StringInput)

	gitDns, err := common.NewDnsRecord(ctx, "gitea-dns", "git", labZone, "A", tmp)
	if err != nil {
		return nil, err
	}

	ctx.Export("git_url", pulumi.String(gitDns.DnsName))

	return gitMain, nil
}

func main() {
	pulumi.Run(func(ctx *pulumi.Context) error {

		project := "galaxygridlabs"
		region := "us-central1"
		labZone := "galaxygridlabs-com"

		// _, err := common.NewNetwork(ctx, "lab-net", project, region, "main")
		// if err != nil {
		// 	return err
		// }

		vaultMain, err := setupVault(ctx, project, region, labZone)
		if err != nil {
			return err
		}

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

			// Setup OIDC with google

			_, err = setupGitea(ctx, project, region, labZone)
			if err != nil {
				return err
			}

			return nil
		})

		return nil
	})
}
