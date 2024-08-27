package common

import (
	"fmt"

	"github.com/pulumi/pulumi-cloudinit/sdk/go/cloudinit"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

type CloudInitData struct {
	pulumi.ResourceState
	Id       string
	Data     pulumi.String
	Rendered pulumi.StringOutput
}

func NewCloudInitData(ctx *pulumi.Context, name string, data string, resourceId string) (*CloudInitData, error) {

	dataRes := &CloudInitData{
		Id:   resourceId,
		Data: pulumi.String(data),
	}

	err := ctx.RegisterComponentResource(fmt.Sprintf("pkg:index:gcp:cloudinitdata:%s", resourceId), name, dataRes)
	if err != nil {
		return nil, err
	}

	config, err := cloudinit.NewConfig(ctx, "configResource", &cloudinit.ConfigArgs{
		Base64Encode: pulumi.Bool(false),
		Gzip:         pulumi.Bool(false),
		Parts: cloudinit.ConfigPartArray{
			&cloudinit.ConfigPartArgs{
				Content:     pulumi.String(data),
				ContentType: pulumi.String("text/cloud-config"),
				Filename:    pulumi.String("conf.yaml"),
			},
		},
	})
	if err != nil {
		return nil, err
	}

	ctx.RegisterResourceOutputs(dataRes, pulumi.Map{
		"data":     dataRes.Data,
		"rendered": config.Rendered,
	})

	dataRes.Rendered = config.Rendered

	return dataRes, nil
}
