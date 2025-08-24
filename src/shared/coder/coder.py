import re
import pulumi
import pulumi_harvester as harvester
import pulumi_ct as ct
import pulumiverse_time as time
import pulumi_random as random

from shared.harvester.images import CONTAINER_SYSEXT_COMPOSE, DEFAULT_CONTAINER_IMAGE
from shared.harvester.networks import DEFAULT_NETWORK
from shared.cloudflare_tunnel.tunnel import Tunnel

CODER_IMAGE = "ghcr.io/coder/coder:v2.25.1@sha256:e1f1878546a26a787a6ac34a4f83555aec75e6345e17eb49406a02f127787281"
CODER_DISK_SIZE = "16Gi"
CODER_PORT = 7080

POSTGRES_IMAGE = "docker.io/library/postgres:17.6-alpine@sha256:3406990b6e4c7192317b6fdc5680498744f6142f01f0287f4ee0420d8c74063c"


CADDY_IMAGE = "docker.io/library/caddy:2.9-alpine@sha256:9cc41f26f734861421d99f00fc962b3a3181aab9b4eb5c9324efe3b8e8a48612423dd912f76fa93cf138923e7eda5d1a9805057757dbd0ac7751a883623794b6"
CFTUNNEL_IMAGE = "docker.io/cloudflare/cloudflared:2025.8.0"


COS_IMAGE = "harvester-public/flatcar-latest"
COS_DISK_SIZE = "10Gi"


class Coder(pulumi.ComponentResource):
    def __init__(self, name, namespace, opts=None):
        super().__init__("ggl:coder:Coder", name, {}, opts)

        password = random.RandomPassword(
            "postgres_password", length=8, number=False, upper=False, special=False
        )

        coder_db_username = "coder"
        coder_db_database = "coder"
        coder_ext_hostname = "https://coder.astral-labs.work"

        config = pulumi.Config()
        coder_oidc_client_id = config.require("coder_oidc_client_id")
        coder_oidc_client_secret = config.require("coder_oidc_client_secret")

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

        power_off_hook = pulumi.ResourceHook("power_off", power_off)

        coder_tunnel = Tunnel(
            name="coder",
            opts=pulumi.ResourceOptions(
                parent=self,
                hooks=pulumi.ResourceHookBinding(before_delete=[power_off_hook]),
            ),
        )

        pulumi.export("coder_tunnel_token", coder_tunnel.token)
        # Create a Harvester VM for the coder app
        coder_config = pulumi.Output.all(
            passwd=password.result, tunnel_token=coder_tunnel.token
        ).apply(
            lambda args: ct.get_config(
                content=f"""variant: flatcar
version: 1.0.0
# This is a simple NGINX example.
# Replace the below with your own config.
# Refer to https://www.flatcar.org/docs/latest/provisioning/config-transpiler/configuration/ for more information.
systemd:
  units:
    - name: coder.service
      enabled: true
      contents: |
        [Unit]
        Description=CODER App
        After=docker.service
        Requires=docker.service
        [Service]
        TimeoutStartSec=0
        WorkingDirectory=/etc/coder/
        ExecStart=/usr/bin/docker compose up
        ExecStop=/usr/bin/docker compose stop
        Restart=always
        RestartSec=5s
        [Install]
        WantedBy=multi-user.target
storage:
    filesystems:
        - device: /dev/disk/by-path/pci-0000:02:00.0
          format: ext4
          path: /data
          wipe_filesystem: false
    files:
        - path: /etc/coder/cloudflared.env
          mode: 0400
          contents:
            inline: |
                TUNNEL_TOKEN={args['tunnel_token']}
        - path: /etc/coder/postgres.env
          mode: 0400
          contents:
            inline: |
                POSTGRES_USER={coder_db_username}
                POSTGRES_PASSWORD={args['passwd']}
                POSTGRES_DB={coder_db_database}
                PGDATA=/var/lib/postgresql/data
        - path: /etc/coder/coder.env
          mode: 0400
          contents:
            inline: |
                CODER_PG_CONNECTION_URL: "postgresql://{coder_db_username}:{args['passwd']}@database/{coder_db_database}?sslmode=disable"
                CODER_HTTP_ADDRESS: "0.0.0.0:{CODER_PORT}"
                CODER_ACCESS_URL: "{coder_ext_hostname}"
                CODER_OIDC_ISSUER_URL="https://vault.galaxygridlabs.com/v1/identity/oidc/provider/coder"
                CODER_OIDC_EMAIL_DOMAIN="hul.to"
                CODER_OIDC_CLIENT_ID="{coder_oidc_client_id}"
                CODER_OIDC_CLIENT_SECRET="{coder_oidc_client_secret}"
                CODER_OIDC_IGNORE_EMAIL_VERIFIED=true
                CODER_OIDC_SCOPES=openid,email,profile,coder
        - path: /etc/coder/docker-compose.yaml
          mode: 0600
          contents:
            inline: |
                services:
                    coder:
                        # This MUST be stable for our documentation and
                        # other automations.
                        image: {CODER_IMAGE}
                        env_file: /etc/coder/coder.env
                        ports:
                          - "{CODER_PORT}:{CODER_PORT}"
                        group_add:
                          - "233" # docker group on host
                        volumes:
                          - /var/run/docker.sock:/var/run/docker.sock
                        depends_on:
                            database:
                                condition: service_healthy
                    database:
                        image: {POSTGRES_IMAGE}
                        env_file: /etc/coder/postgres.env
                        volumes:
                          - /data:/var/lib/postgresql/data # Use "docker volume rm coder_coder_data" to reset Coder
                        healthcheck:
                            test:
                              [
                                "CMD-SHELL",
                                "pg_isready -U {coder_db_username} -d {coder_db_database}",
                              ]
                            interval: 5s
                            timeout: 5s
                            retries: 5
                    cloudflared:
                        image: {CFTUNNEL_IMAGE}
                        env_file: /etc/coder/cloudflared.env
                        command: tunnel run --url http://coder:{CODER_PORT}
kernel_arguments:
  should_exist:
    - flatcar.autologin
""",
                strict=True,
                pretty_print=False,
                snippets=[CONTAINER_SYSEXT_COMPOSE],
            )
        )

        coder_data = harvester.Volume(
            resource_name=f"{name}data",
            namespace=namespace,
            size=CODER_DISK_SIZE,
            opts=pulumi.ResourceOptions(
                parent=self,
            ),
        )

        coder_cloudinit = harvester.CloudinitSecret(
            resource_name=f"{name}cloudinit",
            namespace=namespace,
            user_data=coder_config.rendered,
            opts=pulumi.ResourceOptions(parent=self),
        )

        coder_vm = harvester.Virtualmachine(
            name,
            name=name,
            namespace=namespace,
            cpu=2,
            memory="4Gi",
            hostname=name,
            efi=True,
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
                    "name": "coder-data",
                    "type": "disk",
                    "auto_delete": False,
                    "existing_volume_name": coder_data.name,
                    "size": CODER_DISK_SIZE,
                    "image": DEFAULT_CONTAINER_IMAGE,
                    "bus": "virtio",
                    "hot_plug": True,
                },
            ],
            network_interfaces=[
                harvester.VirtualmachineNetworkInterfaceArgs(
                    name="nic1",
                    network_name=DEFAULT_NETWORK,
                )
            ],
            cloudinit={
                "type": "configDrive",
                "user_data_secret_name": coder_cloudinit.name,
            },
            opts=pulumi.ResourceOptions(
                parent=self,
                replace_on_changes=["*"],
                delete_before_replace=True,
            ),
        )
