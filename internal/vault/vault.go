package vault

import (
	"fmt"

	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/cloudrun"
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
	Url       pulumi.StringPtrOutput
	RootToken string
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

	vaultConfig := &cloudrun.ServiceTemplateSpecContainerEnvArgs{
		Name:  pulumi.String("VAULT_LOCAL_CONFIG"),
		Value: configValue,
	}
	// 						Image: pulumi.String("docker.io/hashicorp/vault:1.17.2@sha256:aaaedf0b3b34560157cc7c06f50f794eb7baa071165f2eed4db94b44db901806"),

	// Create a Cloud Run service definition.
	service, err := cloudrun.NewService(ctx, "vault", &cloudrun.ServiceArgs{
		Location: pulumi.String("us-central1"),
		Template: cloudrun.ServiceTemplateArgs{
			Metadata: cloudrun.ServiceTemplateMetadataArgs{
				Annotations: &pulumi.StringMap{
					"run.googleapis.com/cpu-throttling": pulumi.String("false"),
				},
			},
			Spec: cloudrun.ServiceTemplateSpecArgs{
				ServiceAccountName: vaultSvcAccount.Email,
				Containers: cloudrun.ServiceTemplateSpecContainerArray{
					cloudrun.ServiceTemplateSpecContainerArgs{
						Image: pulumi.String("docker.io/hashicorp/vault:1.16.2@sha256:e139ff28c23e1f22a6e325696318141259b177097d8e238a3a4c5b84862fadd8"),
						Resources: cloudrun.ServiceTemplateSpecContainerResourcesArgs{
							Limits: pulumi.ToStringMap(map[string]string{
								"memory": "512Mi",
								"cpu":    "1",
							}),
						},
						Ports: cloudrun.ServiceTemplateSpecContainerPortArray{
							cloudrun.ServiceTemplateSpecContainerPortArgs{
								ContainerPort: pulumi.Int(8200),
							},
						},
						Args: &pulumi.StringArray{
							pulumi.String("server"),
						},
						Envs: cloudrun.ServiceTemplateSpecContainerEnvArray{
							&cloudrun.ServiceTemplateSpecContainerEnvArgs{
								Name:  pulumi.String("SKIP_SETCAP"),
								Value: pulumi.String("true"),
							},
							vaultConfig,
						},
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

	vaultRes.Url = service.Statuses.Index(pulumi.Int(0)).Url()

	// Wait for the app to be published
	published.Project.ApplyT(func(_ any) error {
		res, err := vaultRes.VaultInit(ctx)
		if err != nil {
			return err
		}
		fmt.Printf("res: %v\n", res)
		vaultRes.RootToken = res.RootToken
		return nil
	})

	ctx.RegisterResourceOutputs(vaultRes, pulumi.Map{
		"root_token": pulumi.String(vaultRes.RootToken),
		"url":        vaultRes.Url,
		"id":         pulumi.String(vaultRes.Id),
	})
	return vaultRes, nil
}
