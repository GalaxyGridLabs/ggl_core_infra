import pulumi_harvester as harvester

DEFAULT_IMAGE = "harvester-public/ubuntu-server-noble-24.04"
DEFAULT_CONTAINER_IMAGE = "harvester-public/flatcar-latest"

IMAGES = {
    "ubuntu-server-noble-24.04": {
        "url": "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img",
        "os": "ubuntu",
        "arch": "amd64",
        "description": "Ubuntu Server 24.04 LTS (Noble)",
    },
    "ubuntu-server-jammy-22.04": {
        "url": "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img",
        "os": "ubuntu",
        "arch": "amd64",
        "description": "Ubuntu Server 22.04 LTS (Jammy)",
    },
    "ubuntu-server-focal-20.04": {
        "url": "https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img",
        "os": "ubuntu",
        "arch": "amd64",
        "description": "Ubuntu Server 20.04 LTS (Focal)",
    },
    "ubuntu-server-bionic-18.04": {
        "url": "https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img",
        "os": "ubuntu",
        "arch": "amd64",
        "description": "Ubuntu Server 18.04 LTS (Bionic)",
    },
    "ubuntu-server-xenial-16.04": {
        "url": "https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img",
        "os": "ubuntu",
        "arch": "amd64",
        "description": "Ubuntu Server 16.04 LTS (Xenial)",
    },
    "ubuntu-server-trusty-14.04": {
        "url": "https://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img",
        "os": "ubuntu",
        "arch": "amd64",
        "description": "Ubuntu Server 14.04 LTS (Trusty)",
    },
    "debian-trixie-13": {
        "url": "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-generic-amd64.qcow2",
        "os": "debian",
        "arch": "amd64",
        "description": "Debian 13 (Trixie)",
    },
    "debian-bookworm-12": {
        "url": "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2",
        "os": "debian",
        "arch": "amd64",
        "description": "Debian 12 (Bookworm)",
    },
    "debian-bullseye-11": {
        "url": "https://cloud.debian.org/images/cloud/bullseye/latest/debian-11-generic-amd64.qcow2",
        "os": "debian",
        "arch": "amd64",
        "description": "Debian 11 (Bullseye)",
    },
    "debian-buster-10": {
        "url": "https://cloud.debian.org/images/cloud/buster/latest/debian-10-generic-amd64.qcow2",
        "os": "debian",
        "arch": "amd64",
        "description": "Debian 10 (Buster)",
    },
    "debian-stretch-9": {
        "url": "https://cdimage.debian.org/cdimage/openstack/9.13.42-20220706/debian-9.13.42-20220706-openstack-amd64.qcow2",
        "os": "debian",
        "arch": "amd64",
        "description": "Debian 9 (Stretch)",
    },
    "debian-jessie-8": {
        "url": "https://cloud.debian.org/images/cloud/OpenStack/archive/8.10.0/debian-8.10.0-openstack-amd64.qcow2",
        "os": "debian",
        "arch": "amd64",
        "description": "Debian 8 (Jessie)",
    },
    "rocky-10": {
        "url": "https://dl.rockylinux.org/pub/rocky/10/images/x86_64/Rocky-10-GenericCloud-Base.latest.x86_64.qcow2",
        "os": "rocky",
        "arch": "amd64",
        "description": "Rocky 10",
    },
    "rocky-9": {
        "url": "https://dl.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud-Base.latest.x86_64.qcow2",
        "os": "rocky",
        "arch": "amd64",
        "description": "Rocky 9",
    },
    "rocky-8": {
        "url": "https://dl.rockylinux.org/pub/rocky/8/images/x86_64/Rocky-8-GenericCloud-Base.latest.x86_64.qcow2",
        "os": "rocky",
        "arch": "amd64",
        "description": "Rocky 8",
    },
    "centos-10": {
        "url": "https://cloud.centos.org/centos/10-stream/x86_64/images/CentOS-Stream-GenericCloud-10-latest.x86_64.qcow2",
        "os": "centos",
        "arch": "amd64",
        "description": "Centos 10",
    },
    "centos-9": {
        "url": "https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-9-latest.x86_64.qcow2",
        "os": "centos",
        "arch": "amd64",
        "description": "Centos 9",
    },
    "centos-8": {
        "url": "https://cloud.centos.org/centos/8-stream/x86_64/images/CentOS-Stream-GenericCloud-8-latest.x86_64.qcow2",
        "os": "centos",
        "arch": "amd64",
        "description": "Centos 8",
    },
    "fedora-42": {
        "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/42/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-42-1.1.x86_64.qcow2",
        "os": "fedora",
        "arch": "amd64",
        "description": "Fedora 42",
    },
    "fedora-41": {
        "url": "https://ftp-osl.osuosl.org/pub/fedora/linux/releases/41/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-41-1.4.x86_64.qcow2",
        "os": "fedora",
        "arch": "amd64",
        "description": "Fedora 41",
    },
    "flatcar-latest": {
        "url": "https://stable.release.flatcar-linux.net/amd64-usr/current/flatcar_production_kubevirt_image.qcow2",
        "os": "flatcar",
        "arch": "amd64",
        "description": "FlatCar Container Linux (latest)",
    },
    "windows25-runner": {
        "url": "https://md-gfmhgbfz5m5l.z23.blob.storage.azure.net/g2wqrnpqqshn/abcd?sv=2018-03-28&sr=b&si=71bbbf8f-e2dd-4b6f-a700-da2fad4819b9&sig=zsUgX0iZqpDnDs5AJYj52wKL%2Fx257qslppiIERwNBZE%3D",
        "os": "windows",
        "arch": "amd64",
        "description": "Windows Server 2025 Github Actions Runner",
        "timeouts": {
            "create": "36000",
            "update": "36000",
        },
    },
}

IMAGES_PULUMI = {}

CONTAINER_SYSEXT_COMPOSE = """variant: flatcar
version: 1.0.0

storage:
  files:
    - path: /opt/extensions/docker-compose/docker-compose-2.34.0-x86-64.raw
      mode: 0644
      contents:
        source: https://extensions.flatcar.org/extensions/docker-compose-2.34.0-x86-64.raw
    - path: /etc/sysupdate.docker-compose.d/docker-compose.conf
      contents:
        source: https://extensions.flatcar.org/extensions/docker-compose.conf
    - path: /etc/sysupdate.d/noop.conf
      contents:
        source: https://extensions.flatcar.org/extensions/noop.conf
  links:
    - target: /opt/extensions/docker-compose/docker-compose-2.34.0-x86-64.raw
      path: /etc/extensions/docker-compose.raw
      hard: false
systemd:
  units:
    - name: systemd-sysupdate.timer
      enabled: true
    - name: systemd-sysupdate.service
      dropins:
        - name: docker-compose.conf
          contents: |
            [Service]
            ExecStartPre=/usr/bin/sh -c "readlink --canonicalize /etc/extensions/docker-compose.raw > /tmp/docker-compose"
            ExecStartPre=/usr/lib/systemd/systemd-sysupdate -C docker-compose update
            ExecStartPost=/usr/bin/sh -c "readlink --canonicalize /etc/extensions/docker-compose.raw > /tmp/docker-compose-new"
            ExecStartPost=/usr/bin/sh -c "if ! cmp --silent /tmp/docker-compose /tmp/docker-compose-new; then touch /run/reboot-required; fi"
"""


def create_image(name, image_def):
    """Create a harvester image."""
    return harvester.Image(
        name,
        name=name,
        display_name=name,
        description=image_def["description"],
        namespace="harvester-public",
        source_type="download",
        url=image_def["url"],
        tags={
            "os-type": image_def["os"],
            "arch": image_def["arch"],
        },
    )


def create_all_images():
    """Create all harvester images."""
    for name, image_def in IMAGES.items():
        IMAGES_PULUMI[name] = create_image(name, image_def)
