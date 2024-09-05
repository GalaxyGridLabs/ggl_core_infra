package common

import (
	"fmt"

	"github.com/pulumi/pulumi-gcp/sdk/v7/go/gcp/dns"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

type DnsRecord struct {
	pulumi.ResourceState
	Id      string
	DnsName string
	Type    string
	Rrdata  pulumi.StringInput
}

func NewDnsRecord(ctx *pulumi.Context, name string, dnsname string, managedzone string, rtype string, rrdata pulumi.StringInput) (*DnsRecord, error) {

	envDnsZone, err := dns.LookupManagedZone(ctx, &dns.LookupManagedZoneArgs{
		Name: managedzone,
	}, nil)
	if err != nil {
		return nil, err
	}

	dnsRes := &DnsRecord{
		Type:    rtype,
		DnsName: fmt.Sprintf("%s.%s", dnsname, envDnsZone.DnsName),
		Rrdata:  rrdata,
	}

	_, err = dns.NewRecordSet(ctx, name, &dns.RecordSetArgs{
		Name:        pulumi.Sprintf("%s.%v", dnsname, envDnsZone.DnsName),
		Type:        pulumi.String(rtype),
		Ttl:         pulumi.Int(300),
		ManagedZone: pulumi.String(envDnsZone.Name),
		Rrdatas: pulumi.StringArray{
			rrdata,
		},
	})
	if err != nil {
		return nil, err
	}

	err = ctx.RegisterComponentResource("pkg:index:gcp:dnsrecord", name, dnsRes)
	if err != nil {
		return nil, err
	}

	ctx.RegisterResourceOutputs(dnsRes, pulumi.Map{
		"DnsName": pulumi.String(dnsRes.DnsName),
		"Type":    pulumi.String(dnsRes.Type),
		"Rrdata":  rrdata,
	})

	return dnsRes, nil
}
