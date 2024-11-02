package git

import (
	"fmt"
	"ggl_core_infra/internal/common"

	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/compute"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

const giteaDataDiskSizeGB = 12

type Gitea struct {
	pulumi.ResourceState
	Id        string
	MapOutput pulumi.Map
}

func NewGitea(ctx *pulumi.Context, gcpProject string, gcpRegion string, resourceId string) (*Gitea, error) {
	// Setup boiler plate
	gitRes := &Gitea{
		Id: resourceId,
	}

	err := ctx.RegisterComponentResource(fmt.Sprintf("pkg:index:gcp:Gitea:%s", resourceId), "gitea", gitRes)
	if err != nil {
		return nil, err
	}

	// Create gitea storage disk
	dataDisk, err := compute.NewDisk(ctx, "giteadata", &compute.DiskArgs{
		Size: pulumi.Int(giteaDataDiskSizeGB),
	})
	if err != nil {
		return nil, err
	}

	// Create the virtual machine.
	// TODO:
	// - Connect to vault oauth2 https://github.com/go-gitea/gitea/blob/1e4be0945b466a17cd98b5aed19faf6caad12fb4/custom/conf/app.example.ini#L1549
	// - Disable install page https://docs.gitea.com/administration/config-cheat-sheet#security-security
	// - Automate install step
	// - [X] Persist config
	// - [X] Persist database
	// - Backup config & database
	// - Test DB and Config restore
	// - Enable ssh for cloning repos but not management. - Maybe different port?
	// - Setup port redir
	// - Setup DNS
	// - Setup TLS with vault PKI.

	// image: docker.io/gitea/gitea:1.22.0@sha256:ff5addffde6abf6e57a7def08f45281eab2a86d2ff6cd92ac88ff84263a87547
	// Define docker image spec
	specStr := `
spec:
  containers:
  - name: gitea
    image: docker.io/gitea/gitea:1.22.3@sha256:76f516a1a8c27e8f8e9773639bf337c0176547a2d42a80843e3f2536787341c6
    env:
    - name: DISABLE_REGISTRATION
      value: 'false'
    - name: USER_UID
      value: '1000'
    - name: USER_GID
      value: '1000'
    volumeMounts:
    - name: pd-0
      readOnly: false
      mountPath: /data
    stdin: false
    tty: false
  volumes:
  - name: pd-0
    gcePersistentDisk:
      pdName: giteadata
      fsType: ext4
      partition: 0
      readOnly: false`

	containerSpec, err := common.NewSpec(ctx, "giteaspec", specStr, resourceId, nil)
	if err != nil {
		return nil, err
	}

	// GCP user-data
	// 	cloudInitMetadata, err := common.NewCloudInitData(ctx, "cloudinitdata", `
	// #cloud-config

	// # Create an empty file on the system
	// write_files:
	// - path: /var/win.txt
	// `, resourceId)
	// 	if err != nil {
	// 		return nil, err
	// 	}

	// Create new Container Optomized OS VM - running gitea
	instance, err := compute.NewInstance(ctx, "gitea", &compute.InstanceArgs{
		MachineType: pulumi.String("f1-micro"),
		BootDisk: compute.InstanceBootDiskArgs{
			InitializeParams: compute.InstanceBootDiskInitializeParamsArgs{
				Image: pulumi.String("projects/cos-cloud/global/images/cos-stable-113-18244-151-9"),
				Size:  pulumi.Int(10),
			},
		},
		AttachedDisks: compute.InstanceAttachedDiskArray{
			compute.InstanceAttachedDiskArgs{
				DeviceName: pulumi.String("giteadata"),
				Mode:       pulumi.String("READ_WRITE"),
				Source:     dataDisk.Name,
			},
		},
		NetworkInterfaces: compute.InstanceNetworkInterfaceArray{
			compute.InstanceNetworkInterfaceArgs{
				AccessConfigs: compute.InstanceNetworkInterfaceAccessConfigArray{
					&compute.InstanceNetworkInterfaceAccessConfigArgs{ // PREMIUM Tier doesn't allocate an ephemeral IP.
						NatIp:       pulumi.String(""),
						NetworkTier: pulumi.String("STANDARD"),
					},
				},
				Subnetwork: pulumi.String("default"),
				StackType:  pulumi.String("IPV4_ONLY"),
			},
		},
		ServiceAccount: compute.InstanceServiceAccountArgs{
			Scopes: pulumi.ToStringArray([]string{
				"https://www.googleapis.com/auth/cloud-platform",
			}),
		},
		AllowStoppingForUpdate: pulumi.Bool(true),
		Metadata: pulumi.StringMap{
			"gce-container-declaration": pulumi.String(containerSpec.Spec),
			"google-logging-enabled":    pulumi.String("false"),
			// "user-data":                 cloudInitMetadata.Rendered,
		},
		Tags: pulumi.ToStringArray([]string{}),
	}, pulumi.Parent(gitRes), pulumi.DeleteBeforeReplace(true), pulumi.ReplaceOnChanges([]string{"metadata"}))
	if err != nil {
		return nil, err
	}

	gitRes.MapOutput = pulumi.Map{
		"url": instance.NetworkInterfaces,
	}
	ctx.RegisterResourceOutputs(gitRes, gitRes.MapOutput)
	return gitRes, nil
}
