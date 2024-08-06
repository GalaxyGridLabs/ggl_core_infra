package vault

import (
	"encoding/json"
	"fmt"
	"log"

	"github.com/pulumi/pulumi-command/sdk/go/command/local"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/cloudrun"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/cloudrunv2"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/kms"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/projects"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/serviceaccount"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/storage"
	"github.com/pulumi/pulumi-random/sdk/v4/go/random"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

type HashicorpVault struct {
	pulumi.ResourceState
	Id        string
	MapOutput pulumi.Map
}

type InitResponse struct {
	Keys       []string `json:"keys"`
	KeysBase64 []string `json:"keys_base64"`
	RootToken  string   `json:"root_token"`
}

func NewVault(ctx *pulumi.Context, gcpProject string, gcpRegion string, resourceId string) (*HashicorpVault, error) {
	vaultRes := &HashicorpVault{
		Id: resourceId,
	}

	err := ctx.RegisterComponentResource(fmt.Sprintf("pkg:index:gcp:HashicorpVault:%s", resourceId), "vault", vaultRes)
	if err != nil {
		return nil, err
	}

	// Create key for vault
	gcpKmsRegion := "global"
	vaultKeyRing, err := kms.NewKeyRing(ctx, "vault-keys", &kms.KeyRingArgs{
		Location: pulumi.String(gcpKmsRegion),
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	unsealKey, err := kms.NewCryptoKey(ctx, "vault-key", &kms.CryptoKeyArgs{
		KeyRing:        vaultKeyRing.ID(),
		RotationPeriod: pulumi.String("100000s"),
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	// Create service account for vault
	vaultSvcAccNameHex, err := random.NewRandomId(ctx, "vault-svc-id", &random.RandomIdArgs{
		ByteLength: pulumi.Int(6),
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	vaultSvcAccount, err := serviceaccount.NewAccount(ctx, "vault-svc", &serviceaccount.AccountArgs{
		AccountId: vaultSvcAccNameHex.Hex.ApplyT(func(h string) (string, error) {
			return fmt.Sprintf("svc-vault-storage-%s", h), nil
		}).(pulumi.StringOutput),
		DisplayName: pulumi.String("Vault Storage Admin"),
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	// Assign service account permissions
	saEmail := vaultSvcAccount.Email.ToStringOutput().ApplyT(func(s string) string {
		return "serviceAccount:" + s
	}).(pulumi.StringInput)

	_, err = projects.NewIAMMember(ctx, gcpProject, &projects.IAMMemberArgs{
		Project: pulumi.String(gcpProject),
		Role:    pulumi.String("roles/storage.objectAdmin"),
		Member:  saEmail,
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	_, err = kms.NewKeyRingIAMMember(ctx, "vault-svc-key-ring-role", &kms.KeyRingIAMMemberArgs{
		KeyRingId: vaultKeyRing.ID(),
		Member:    saEmail,
		Role:      pulumi.String("roles/owner"),
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	// Create bucket to store vault stuff
	vaultStorage, err := storage.NewBucket(ctx, "ggl-vault-storage", &storage.BucketArgs{
		Location:               pulumi.String("US"),
		ForceDestroy:           pulumi.Bool(true),
		PublicAccessPrevention: pulumi.String("enforced"),
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	// vault config
	configValue := pulumi.All(vaultStorage.Name, unsealKey.Name, vaultKeyRing.Name).ApplyT(
		func(args []interface{}) pulumi.StringOutput {
			bucketName := args[0]
			unsealkeyName := args[1]
			vaultKeyRingName := args[2]
			return pulumi.Sprintf(`
				ui                = true

				storage "gcs" {
					bucket = "%s"
				}

				listener "tcp" {
					address       = "0.0.0.0:8200"
					tls_disable   = true
				}

				seal "gcpckms" {
					project     = "%s"
					region      = "%s"
					key_ring    = "%s"
					crypto_key  = "%s"
				}`, bucketName, gcpProject, gcpKmsRegion, vaultKeyRingName, unsealkeyName)
		},
	).(pulumi.StringInput)

	vaultConfig := &cloudrunv2.ServiceTemplateContainerEnvArgs{
		Name:  pulumi.String("VAULT_LOCAL_CONFIG"),
		Value: configValue,
	}
	// 						Image: pulumi.String("docker.io/hashicorp/vault:1.17.2@sha256:aaaedf0b3b34560157cc7c06f50f794eb7baa071165f2eed4db94b44db901806"),

	// Create a Cloud Run service definition.
	service, err := cloudrunv2.NewService(ctx, "vault", &cloudrunv2.ServiceArgs{
		Location: pulumi.String("us-central1"),
		Template: cloudrunv2.ServiceTemplateArgs{
			Annotations: &pulumi.StringMap{
				"run.googleapis.com/cpu-throttling": pulumi.String("false"),
			},
			ServiceAccount: vaultSvcAccount.Email,
			Containers: cloudrunv2.ServiceTemplateContainerArray{
				cloudrunv2.ServiceTemplateContainerArgs{
					Image: pulumi.String("docker.io/hashicorp/vault:1.16.2@sha256:e139ff28c23e1f22a6e325696318141259b177097d8e238a3a4c5b84862fadd8"),
					Resources: cloudrunv2.ServiceTemplateContainerResourcesArgs{
						Limits: pulumi.ToStringMap(map[string]string{
							"memory": "512Mi",
							"cpu":    "1",
						}),
					},
					Ports: cloudrunv2.ServiceTemplateContainerPortArray{
						cloudrunv2.ServiceTemplateContainerPortArgs{
							ContainerPort: pulumi.Int(8200),
						},
					},
					Args: &pulumi.StringArray{
						pulumi.String("server"),
					},
					Envs: cloudrunv2.ServiceTemplateContainerEnvArray{
						&cloudrunv2.ServiceTemplateContainerEnvArgs{
							Name:  pulumi.String("SKIP_SETCAP"),
							Value: pulumi.String("true"),
						},
						vaultConfig,
					},
				},
			},
		},
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	// Make vault publicly accessible
	published, err := cloudrun.NewIamBinding(ctx, "vault-svc-public-binding", &cloudrun.IamBindingArgs{
		Location: service.Location,
		Service:  service.Name,
		Role:     pulumi.String("roles/run.invoker"),
		Members: pulumi.StringArray{
			pulumi.String("allUsers"),
		},
	}, pulumi.Parent(vaultRes))
	if err != nil {
		return nil, err
	}

	// Wait for the app to be created and published
	rootToken := pulumi.All(published.Project, service.Uri).ApplyT(
		// Initialize pulumi
		func(args []interface{}) pulumi.StringOutput {
			uri := args[1]

			initPayload := `{
	"recovery_shares": 5,
	"recovery_threshold": 3,
	"stored_shares": 5
}`

			cmdRes, err := local.NewCommand(ctx, resourceId, &local.CommandArgs{
				Create: pulumi.String(fmt.Sprintf("curl -s -X POST --data '%s' %s/v1/sys/init", initPayload, uri)),
			})
			if err != nil {
				return pulumi.StringOutput{}
			}

			cmdRes.Stderr.ApplyT(func(e string) error {
				if len(e) > 0 {
					log.Printf("Init errors: %s\n", e)
				}
				return nil
			})

			out := cmdRes.Stdout.ApplyT(func(o string) (string, error) {
				var initResponse InitResponse

				if err := json.Unmarshal([]byte(o), &initResponse); err != nil {
					log.Println(err)
					return o, nil
				}

				return initResponse.RootToken, nil
			}).(pulumi.StringOutput)

			return out
		},
	).(pulumi.StringOutput)

	vaultRes.MapOutput = pulumi.Map{
		"root_token": rootToken,
		"url":        service.Uri,
	}
	ctx.RegisterResourceOutputs(vaultRes, vaultRes.MapOutput)
	return vaultRes, nil
}
