package vault

import (
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/cloudrun"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/kms"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/projects"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/serviceaccount"
	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/storage"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

func NewVault(ctx *pulumi.Context, gcpProject string, gcpRegion string) error {
	// Create key for vault
	vaultKeyRingName := "vault-keys-xise3a"

	// vaultKeyRing, err := kms.GetKMSKeyRing(ctx, &kms.GetKMSKeyRingArgs{
	// 	Name:     vaultKeyRingName,
	// 	Location: "us-east4",
	// }, nil)
	// if err != nil {
	// 	return err
	// }

	vaultKeyRing, err := kms.NewKeyRing(ctx, "keyring", &kms.KeyRingArgs{
		Name:     pulumi.String(vaultKeyRingName),
		Location: pulumi.String("global"),
	})
	if err != nil {
		return err
	}

	unsealKey, err := kms.NewCryptoKey(ctx, "vault-key", &kms.CryptoKeyArgs{
		Name:           pulumi.String("vault-key-ci8kie"),
		KeyRing:        vaultKeyRing.ID(),
		RotationPeriod: pulumi.String("100000s"),
	})
	if err != nil {
		return err
	}

	// Create service account for vault
	vaultSvcAccount, err := serviceaccount.NewAccount(ctx, "vault-svc", &serviceaccount.AccountArgs{
		AccountId:   pulumi.String("svc-vault-storage"),
		DisplayName: pulumi.String("Vault Storage Admin"),
	})
	if err != nil {
		return err
	}

	// Assign service account permissions
	saEmail := vaultSvcAccount.Email.ToStringOutput().ApplyT(func(s string) string {
		return "serviceAccount:" + s
	}).(pulumi.StringInput)

	_, err = projects.NewIAMMember(ctx, gcpProject, &projects.IAMMemberArgs{
		Project: pulumi.String(gcpProject),
		Role:    pulumi.String("roles/storage.objectAdmin"),
		Member:  saEmail,
	})
	if err != nil {
		return err
	}

	_, err = kms.NewKeyRingIAMMember(ctx, "vaultSvcKeyRingRole", &kms.KeyRingIAMMemberArgs{
		KeyRingId: vaultKeyRing.ID(),
		Member:    saEmail,
		Role:      pulumi.String("roles/owner"),
	})
	if err != nil {
		return err
	}

	// Create bucket to store vault stuff
	vaultStorage, err := storage.NewBucket(ctx, "vault_storage", &storage.BucketArgs{
		Name:                   pulumi.String("ggl_vault_storage_aec0hiarugeigeing"),
		Location:               pulumi.String("US"),
		ForceDestroy:           pulumi.Bool(true),
		PublicAccessPrevention: pulumi.String("enforced"),
	})
	if err != nil {
		return err
	}

	// vault config
	configValue := pulumi.All(vaultStorage.Name, unsealKey.Name).ApplyT(
		func(args []interface{}) pulumi.StringOutput {
			bucketName := args[0]
			unsealkeyName := args[1]
			return pulumi.Sprintf(`

			ui              = true

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
				}`, bucketName, gcpProject, "global", vaultKeyRingName, unsealkeyName)
		},
	).(pulumi.StringInput)

	vaultConfig := &cloudrun.ServiceTemplateSpecContainerEnvArgs{
		Name:  pulumi.String("VAULT_LOCAL_CONFIG"),
		Value: configValue,
	}

	// Create a Cloud Run service definition.
	service, err := cloudrun.NewService(ctx, "new-vault", &cloudrun.ServiceArgs{
		Location: pulumi.String("us-central1"),
		Template: cloudrun.ServiceTemplateArgs{
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
	})
	if err != nil {
		return err
	}

	// Make vault publicly accessible
	_, err = cloudrun.NewIamBinding(ctx, "vaultSvcPublicBinding", &cloudrun.IamBindingArgs{
		Location: service.Location,
		Service:  service.Name,
		Role:     pulumi.String("roles/run.invoker"),
		Members: pulumi.StringArray{
			pulumi.String("allUsers"),
		},
	})
	if err != nil {
		return err
	}

	ctx.Export("url", service.Statuses.Index(pulumi.Int(0)).Url())

	return nil
}
