import pulumi_cloudflare as cloudflare
import pulumi
import base64


import pulumi_random as random


class Tunnel(pulumi.ComponentResource):
    def __init__(self, name, opts=None):
        super().__init__("ggl:cft:Tunnel", name, {}, opts)

        config = pulumi.Config()
        tunnel_name = random.RandomId(
            resource_name=name,
            prefix=f"{name}-",
            byte_length=3,
            opts=pulumi.ResourceOptions(parent=self),
        )

        tunnel = cloudflare.ZeroTrustTunnelCloudflared(
            name,
            name=tunnel_name.hex,
            config_src="local",
            account_id=config.require("account_id"),
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
            ),
        )

        self.token = cloudflare.get_zero_trust_tunnel_cloudflared_token_output(
            account_id=config.require("account_id"), tunnel_id=tunnel.id
        ).token

        pulumi.export("tunnel_id", tunnel.id)
        tunnel.id.apply(
            lambda id: cloudflare.DnsRecord(
                name,
                args=cloudflare.DnsRecordArgs(
                    name=name,
                    zone_id=config.require("zone_id"),
                    type="CNAME",
                    content=f"{id}.cfargotunnel.com",
                    ttl=1,
                    proxied=True,
                ),
                opts=pulumi.ResourceOptions(parent=self),
            )
        )
