package common

import (
	"fmt"

	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

type CosSpec struct {
	pulumi.ResourceState
	Id   string
	Spec string
}

// func parseFmtStrings(spec string, fmtStrings *pulumi.Array) (pulumi.String, error) {
// 	var res pulumi.String

// 	if fmtStrings == nil {
// 		res = pulumi.String(spec)
// 	} else {
// 		res = fmtStrings.ToArrayOutput().ApplyT(func(f []interface{}) (string, error) {

// 		})
// 	}

// 	return res
// }

func NewSpec(ctx *pulumi.Context, name string, spec string, resourceId string, fmtStrings *pulumi.Map) (*CosSpec, error) {

	specRes := &CosSpec{
		Id:   resourceId,
		Spec: spec,
	}

	err := ctx.RegisterComponentResource(fmt.Sprintf("pkg:index:gcp:cosspec:%s", resourceId), name, specRes)
	if err != nil {
		return nil, err
	}

	ctx.RegisterResourceOutputs(specRes, pulumi.Map{
		"spec": pulumi.String(specRes.Spec),
	})

	return specRes, nil
}
