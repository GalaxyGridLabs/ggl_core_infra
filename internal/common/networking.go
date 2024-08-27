package common

import (
	"fmt"

	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/compute"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

type Network struct {
	pulumi.ResourceState
	Id        string
	MapOutput pulumi.Map
}

func NewNetwork(ctx *pulumi.Context, name string, gcpProject string, gcpRegion string, resourceId string) (*Network, error) {
	// Setup boiler plate
	netRes := &Network{
		Id: resourceId,
	}

	err := ctx.RegisterComponentResource(fmt.Sprintf("pkg:index:gcp:Network:%s", resourceId), name, netRes)
	if err != nil {
		return nil, err
	}

	net, err := compute.NewNetwork(ctx, name, nil)
	if err != nil {
		return nil, err
	}

	netRes.MapOutput = pulumi.Map{
		"id": net.ID(),
	}
	ctx.RegisterResourceOutputs(netRes, netRes.MapOutput)
	return netRes, nil
}
