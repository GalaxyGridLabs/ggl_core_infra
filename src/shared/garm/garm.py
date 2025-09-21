import base64
import hashlib
import re
import pulumi
import pulumi_harvester as harvester
import pulumi_ct as ct
import pulumiverse_time as time
import pulumi_random as random

from shared.harvester.images import CONTAINER_SYSEXT_COMPOSE, DEFAULT_CONTAINER_IMAGE
from shared.harvester.networks import DEFAULT_NETWORK
from shared.cloudflare_tunnel.tunnel import Tunnel

GARM_IMAGE = "ghcr.io/cloudbase/garm:v0.1.6@sha256:d13499ea49f7a0433ac2085205bd82498b9411977d32805eec115aab833ebcd8"
GARM_IMAGE = "ghcr.io/hulto/garm-provider-harvester:0.0.2"
GARM_DISK_SIZE = "16Gi"
GARM_PORT = 80

CADDY_IMAGE = "docker.io/library/caddy:2.9-alpine@sha256:9cc41f26f734861421d99f00fc962b3a3181aab9b4eb5c9324efe3b8e8a48612423dd912f76fa93cf138923e7eda5d1a9805057757dbd0ac7751a883623794b6"
CFTUNNEL_IMAGE = "docker.io/cloudflare/cloudflared:2025.8.0"

COS_IMAGE = "harvester-public/flatcar-latest"
COS_DISK_SIZE = "10Gi"


class Garm(pulumi.ComponentResource):
    def __init__(self, name, namespace, opts=None):
        super().__init__("ggl:garm:Garm", name, {}, opts)

        jwtsecret = random.RandomPassword(
            "jwtsecret", length=64, number=False, upper=True, special=False
        )
        dbpassword = random.RandomPassword(
            "dbpassword", length=32, number=False, upper=True, special=False
        )

        def power_off(args: pulumi.ResourceHookArgs):
            try:
                vm = harvester.get_virtualmachine(name=name, namespace=namespace)
                if vm.status.run_strategy != "Halted":
                    pulumi.log.info(f"Powering off VM {vm.metadata.name} ({vm.id})")
                    vm.status.run_strategy = "Halted"
                else:
                    pulumi.log.info(
                        f"VM {vm.metadata.name} ({vm.id}) is already powered off"
                    )
            except Exception as e:
                pulumi.log.warn(f"Could not power off VM {name}: {e}")

        power_off_hook = pulumi.ResourceHook(f"power_off_garm", power_off)

        garm_tunnel = Tunnel(
            name="garm",
            opts=pulumi.ResourceOptions(
                parent=self,
                hooks=pulumi.ResourceHookBinding(before_delete=[power_off_hook]),
            ),
        )

        # Create a Harvester user
        # svcgarm
        # Rancher > Harvester > harvester > RBAC > Cluster Members > Add > svcgarm > Cluster Member
        # Rancher > Harvester > harvester > Project & Namespaces > garm > Edit config > Add > svcgarm > Project Member

        # Create a Harvester VM for the garm app
        config = pulumi.Config()

        garm_config = pulumi.Output.all(
            kubeconfig=config.require_secret("svcgarm_kubeconfig"),
            tunnel_token=garm_tunnel.token,
            jwtsecret=jwtsecret.result,
            dbpassword=dbpassword.result,
        ).apply(
            lambda args: ct.get_config(
                content=f"""variant: flatcar
version: 1.0.0
# Refer to https://www.flatcar.org/docs/latest/provisioning/config-transpiler/configuration/ for more information.
systemd:
  units:
    - name: garm.service
      enabled: true
      contents: |
        [Unit]
        Description=GARM App
        After=setupscripts.service
        Requires=docker.service
        Requires=data.mount
        [Service]
        TimeoutStartSec=0
        WorkingDirectory=/etc/garm/
        ExecStart=/usr/bin/docker compose up
        ExecStop=/usr/bin/docker compose stop
        Restart=always
        RestartSec=5s
        [Install]
        WantedBy=multi-user.target
    - name: setupscripts.service
      enabled: true
      contents: |
        [Unit]
        Description=Run arbitrary setup scripts
        After=docker.service
        Requires=docker.service
        Requires=data.mount
        [Service]
        TimeoutStartSec=0
        WorkingDirectory=/etc/garm/
        ExecStart=/etc/garm/setupscripts.sh
        Restart=never
        [Install]
        WantedBy=multi-user.target
storage:
    filesystems:
        - device: /dev/disk/by-path/pci-0000:02:00.0
          format: ext4
          wipe_filesystem: false
          with_mount_unit: true
          mount_options:
            - rw
          path: /data
    files:
        - path: /etc/garm/garm-provider-harvester.toml
          mode: 0444
          contents:
            inline: |
                namespace = "garm-runners"

                [credentials]
                    kubeconfig = "/etc/garm/harvester-kubeconfig.yaml"
        - path: /etc/garm/config.toml
          mode: 0444
          contents:
            inline: |
                [default]
                enable_webhook_management = true

                [logging]
                enable_log_streamer = true
                log_format = "text"
                log_level = "info"
                log_source = false

                [metrics]
                enable = true
                disable_auth = false

                [jwt_auth]
                secret = "{args['jwtsecret']}"
                time_to_live = "8760h"

                [apiserver]
                bind = "0.0.0.0"
                port = 80
                use_tls = false

                [apiserver.webui]
                    enable = true

                [database]
                backend = "sqlite3"
                passphrase = "{args['dbpassword']}"
                [database.sqlite3]
                    db_file = "/data/garm.db"

                [[provider]]
                name = "harvester"
                provider_type = "external"
                description = "Harvester Provider"
                [provider.external]
                    provider_executable = "/opt/garm/providers.d/garm-provider-harvester"
                    config_file = "/etc/garm/garm-provider-harvester.toml"
        - path: /etc/garm/garm.env
          mode: 0400
          contents:
            inline: |
                GARM_HTTP_ADDRESS: "0.0.0.0:{GARM_PORT}"
        - path: /etc/coder/setupscripts.sh
          mode: 0500
          contents:
            inline: |
                #!/bin/bash
                cat /etc/garm/harvester-kubeconfig.yaml.b64 | base64 -d > /etc/garm/harvester-kubeconfig.yaml
                systemctl disable setupscripts.service
                touch /done
        - path: /etc/garm/harvester-kubeconfig.yaml.b64
          mode: 0400
          contents:
            inline: {base64.b64encode(args['kubeconfig'].encode()).decode()}
        - path: /etc/garm/cloudflared.env
          mode: 0400
          contents:
            inline: |
                TUNNEL_TOKEN={args['tunnel_token']}
        - path: /etc/garm/docker-compose.yaml
          mode: 0600
          contents:
            inline: |
                services:
                    garm:
                        image: {GARM_IMAGE}
                        env_file: /etc/garm/garm.env
                        ports:
                          - "{GARM_PORT}:{GARM_PORT}"
                        group_add:
                          - "233" # docker group on host
                        volumes:
                          - /etc/garm:/etc/garm:ro
                          - /data/garm:/data/:rw
                    cloudflared:
                        image: {CFTUNNEL_IMAGE}
                        env_file: /etc/garm/cloudflared.env
                        command: tunnel run --protocol http2 --url http://garm:{GARM_PORT}
kernel_arguments:
  should_exist:
    - flatcar.autologin
""",
                strict=True,
                pretty_print=False,
                snippets=[CONTAINER_SYSEXT_COMPOSE],
            )
        )

        garm_data = harvester.Volume(
            resource_name=f"{name}data",
            namespace=namespace,
            size=GARM_DISK_SIZE,
            opts=pulumi.ResourceOptions(
                parent=self,
            ),
        )

        garm_cloudinit = harvester.CloudinitSecret(
            resource_name=f"{name}cloudinit",
            namespace=namespace,
            user_data=garm_config.rendered,
            opts=pulumi.ResourceOptions(parent=self),
        )

        def hashit(input_str):
            h = hashlib.new("md5")
            h.update(input_str.encode("utf-8"))
            return str(h.hexdigest())

        garm_vm = harvester.Virtualmachine(
            name,
            name=name,
            namespace=namespace,
            cpu=2,
            memory="4Gi",
            hostname=name,
            efi=False,
            disks=[
                {
                    "name": "rootdisk",
                    "type": "disk",
                    "size": COS_DISK_SIZE,
                    "image": DEFAULT_CONTAINER_IMAGE,
                    "bus": "virtio",
                    "boot_order": 1,
                    "auto_delete": True,
                },
                {
                    "name": "garm-data",
                    "type": "disk",
                    "auto_delete": False,
                    "existing_volume_name": garm_data.name,
                    "bus": "virtio",
                    "hot_plug": True,
                },
            ],
            tags={
                "hash": garm_cloudinit.user_data.apply(
                    lambda user_data: hashit(user_data)
                )
            },
            network_interfaces=[
                harvester.VirtualmachineNetworkInterfaceArgs(
                    name="nic1",
                    network_name=DEFAULT_NETWORK,
                )
            ],
            cloudinit={
                "type": "configDrive",
                "user_data_secret_name": garm_cloudinit.name,
            },
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[garm_cloudinit],
                replace_on_changes=["tags"],
                delete_before_replace=True,
            ),
        )


"""
wget -O garm-cli.tgz https://github.com/cloudbase/garm/releases/download/v0.1.6/garm-cli-linux-amd64.tgz
sudo tar -xzvf ./garm-cli.tgz -C /usr/bin/


garm-cli init --name="local_garm" \
  --url https://garm.astral-labs.work \
  --username root --email root@garm.astral-labs.work \
  --password '[passsword]'

# Requires a PAT with:
# - read metadata
# - Read & Write Administration
# - Read & Write Repository Hooks
garm-cli github credentials add \
  --name garm_test \
  --description "Github App with access to repos" \
  --endpoint github.com \
  --auth-type pat \
  --pat-oauth-token '[pat]'

garm-cli repository add \
    --name garm-test \
    --owner hulto \
    --credentials garm_test \
    --install-webhook \
    --pool-balancer-type roundrobin \
    --random-webhook-secret

garm-cli pool create \
    --os-type linux \
    --os-arch amd64 \
    --enabled=true \
    --flavor e2-small \
    --image projects/ubuntu-os-cloud/global/images/ubuntu-minimal-2404-noble-amd64-v20250828 \
    --min-idle-runners 1 \
    --repo 10e58c2a-1485-41d7-82f9-a894e6ba903d \
    --tags gcp,linux \
    --provider-name gcp


# harvester-public/ubuntu-server-noble-24.04

garm-cli pool create \
    --os-type linux \
    --os-arch amd64 \
    --enabled=true \
    --flavor medium \
    --image harvester-public/image-fv5rd \
    --min-idle-runners 1 \
    --repo 10e58c2a-1485-41d7-82f9-a894e6ba903d \
    --tags gcp,linux \
    --provider-name harvester

"""
