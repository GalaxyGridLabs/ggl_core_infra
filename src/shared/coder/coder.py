import re
import pulumi
import pulumi_harvester as harvester
import pulumi_ct as ct
import pulumiverse_time as time

from shared.harvester.images import CONTAINER_SYSEXT_COMPOSE, DEFAULT_CONTAINER_IMAGE
from shared.harvester.networks import DEFAULT_NETWORK

CODER_IMAGE = "docker.io/codercom/coder:1.44.7-rc.3@sha256:ee182b271aff3c99059d50c4f561d066c40ba0ccf0714b33a7ca041448dc9a3f"
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

        coder_db_username = "coder"
        coder_db_password = "coder"
        coder_db_database = "coder"
        coder_ext_hostname = "coder.internal.galaxygridlabs.com"

        # Create a Harvester VM for the coder app
        coder_config = ct.get_config(
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
        - device: /dev/disk/by-uuid/be9ac778-32d7-49ca-838e-0bad4dc73db2
          format: ext4
          path: /data
          wipe_filesystem: false
    files:
        - path: /etc/coder/postgres.env
          mode: 0400
          contents:
            inline: |
                POSTGRES_USER={coder_db_username}
                POSTGRES_PASSWORD={coder_db_password}
                POSTGRES_DB={coder_db_database}
                PGDATA=/var/lib/postgresql/data
        - path: /etc/coder/coder.env
          mode: 0400
          contents:
            inline: |
                CODER_PG_CONNECTION_URL: "postgresql://{coder_db_username}:{coder_db_password}@database/{coder_db_database}?sslmode=disable"
                CODER_HTTP_ADDRESS: "0.0.0.0:{CODER_PORT}"
                CODER_ACCESS_URL: "{coder_ext_hostname}"
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
kernel_arguments:
  should_exist:
    - flatcar.autologin
""",
            strict=True,
            pretty_print=False,
            snippets=[CONTAINER_SYSEXT_COMPOSE],
        )

        coder_data = harvester.Volume(
            resource_name=f"{name}data",
            namespace=namespace,
            size=CODER_DISK_SIZE,
            opts=pulumi.ResourceOptions(parent=self),
        )

        coder_cloudinit = harvester.CloudinitSecret(
            resource_name=f"{name}cloudinit",
            namespace=namespace,
            user_data=coder_config.rendered,
            opts=pulumi.ResourceOptions(parent=self),
        )

        coder_vm = harvester.Virtualmachine(
            name,
            namespace=namespace,
            cpu=2,
            memory="4Gi",
            hostname=name,
            efi=True,
            disks=[
                {
                    "name": "rootdisk1",
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
