terraform {
  required_providers {
    coder = {
      source = "coder/coder"
      version = "2.10.0"
    }
    harvester = {
      source  = "harvester/harvester"
      version = "0.6.4"
    }
  }
}


provider "coder" {
}

variable "vm-namespace" {
  type = string
  description = "The harvester namespace to deploy VMs into"
}

provider "harvester" {
  kubeconfig = "/kubeconfig.yaml"
}

data "coder_provisioner" "me" {}

data "coder_workspace" "me" {}

data "coder_workspace_owner" "me" {}

module "code-server" {
  count    = data.coder_workspace.me.start_count
  source   = "registry.coder.com/coder/code-server/coder"
  version  = "1.3.1"
  agent_id = coder_agent.dev[0].id
}

module "devcontainers-cli" {
  count    = data.coder_workspace.me.start_count
  source   = "dev.registry.coder.com/modules/devcontainers-cli/coder"
  agent_id = coder_agent.dev[0].id
}



locals {
  oses = [
    {
      name = "Ubuntu Server 24.04 LTS (Noble)",
      value = "harvester-public/ubuntu-server-noble-24.04",
    },
  ]

  git_repos = [
    {
      name = "Realm",
      value = "https://github.com/spellshift/realm.git"
    },
  ]

  home_dir = "/workspace"
  network_name = "harvester-public/harvester-public-net"
  image_namespace = "harvester-public"
  username = data.coder_workspace_owner.me.name
  is_admin = contains(data.coder_workspace_owner.me.groups, "admin")
}


data "coder_parameter" "os_select" {
  name = "os_select"
  display_name = "Choose your operating system"
  form_type = "dropdown"
  default = "harvester-public/ubuntu-server-noble-24.04"
  order = 1
  mutable = true

  dynamic "option" {
    for_each = local.oses
    content {
      name        = option.value.name
      value       = option.value.value
    }
  }
}

data "coder_parameter" "cpu_select" {
  name = "cpu_slider"
  display_name = "CPU Cores Slider"
  description = "Select CPU cores to provision your VM with"

  type = "number"
  form_type = "slider"
  order = data.coder_parameter.os_select.order + 1
  default = 4
  mutable = true

  validation {
    min = 1
    max = 16
  }
}

data "coder_parameter" "mem_select" {
  name = "mem_slider"
  display_name = "Memory select"
  description = "Select memory gigabytes to provision your VM with"

  type = "number"
  form_type = "slider"
  order = data.coder_parameter.cpu_select.order + 1
  default = 8
  mutable = true

  validation {
    min = 1
    max = 32
  }
}

data "coder_parameter" "disk_select" {
  name = "disk_slider"
  display_name = "Disk select"
  description = "Select disk size in gigabytes to provision your VM with"

  type = "number"
  form_type = "slider"
  order = data.coder_parameter.mem_select.order + 1
  default = 32
  mutable = true

  validation {
    min = 12
    max = 128
  }
}

resource "coder_agent" "dev" {
  count        = data.coder_workspace.me.start_count
  arch = "amd64"
  os   = "linux"
  auth = "token"
  dir = local.home_dir
  connection_timeout = 480

  display_apps {
    vscode          = true
    vscode_insiders = false
    web_terminal    = true
    ssh_helper      = false
  }

  env = {
    GIT_AUTHOR_NAME     = coalesce(data.coder_workspace_owner.me.full_name, local.username)
    GIT_AUTHOR_EMAIL    = "${data.coder_workspace_owner.me.email}"
    GIT_COMMITTER_NAME  = coalesce(data.coder_workspace_owner.me.full_name, local.username)
    GIT_COMMITTER_EMAIL = "${data.coder_workspace_owner.me.email}"
  }

  metadata {
    display_name = "CPU Usage"
    key          = "0_cpu_usage"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "RAM Usage"
    key          = "1_ram_usage"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "Workspace disk Usage"
    key  = "wrk_disk"
    script = "df -h --output=pcent /workspace/ | tail -1"
    interval = 10
    timeout = 1
  }

  metadata {
    display_name = "Root disk Usage"
    key  = "root_disk"
    script = "df -h --output=pcent / | tail -1"
    interval = 10
    timeout = 1
  }


}

data "cloudinit_config" "startup" {
  count        = data.coder_workspace.me.start_count
  gzip          = false
  base64_encode = false

  part {
    filename     = "cloud-config.yaml"
    content_type = "text/cloud-config"
    # TODO store ssh key in Vault and reference here based on username.
    # limit access to KV based on user name
    content = <<EOT
#cloud-config
package_upgrade: true
packages:
  - qemu-guest-agent
  - git
  - npm
  - docker-ce
  - docker-ce-cli
apt:
  sources:
    docker.list:
      source: deb [arch=amd64] https://download.docker.com/linux/ubuntu $RELEASE stable
      keyid: 9DC858229FC7DD38854AE2D88D81803C0EBFCD88
fs_setup:
  - device: /dev/vdb
    filesystem: 'ext4'
    label: 'mydata'
    overwrite: false
mounts:
  - [ vdb, ${local.home_dir} ]
write_files:
  - path: /etc/ssh/ca_user_key.pub
    content: |
      ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCp+DQ/EFCKh7Shmo0KhbJN+WHGONDa1cAJ58WumJixrisOXN58euv69QeTMyclpPQluLchRJcIjJcfkWD7s9p5UEzHO+Gca7vaUWpeoyOl5OIWPMW47GcY3Y+H1h4g9mhIfKpbJP2OXNZNBMoSv/94vn5jvU4yAz2dyIp7Qw5Kdy1Vk/hr4kxWr3q++0xU0hOnZ0E1yG7U1ybd9XolKkUnyOGl4sxt5sgv+pQQWoSblPlqVUjaq7/WjF33fbnV2316C/MufNk0K5caAWS4lA3xiw0mF0MHhW04D64xoQvoepUP6awY0HG8LPYcTCY7hpvFNxwJoWn5UpoRaZciE2p1BxWPHqYWwTx0uhJ0MWxOLa7mkBV0c+QEyl3iNDi41gnHElW2yvb1e5GMAWdNMLF21BP8VAnba0Rt0APGNQxUAmNHsXRtF03tkhVITrKw3yEC3NIHiIVQSWJF3H+ehO1SV1n0onWqgkCawkmTe0A+gOW+5G11heEbyNtLHUmxp46wWejPrb1z86ePUgpMCAXstNPYVcxmIcEgBFW/kuxNjF6VIAMzzlHfXZdQQWOT/jAXJPBkrawjVn+DAKxxN1v3RnkK9AzIKE7olmgp8rbVXichIOZUaERfL5kRYMvQvwE4YNU6UnYEA1SexPF/PPCvTZSsrEzFLcNXMNW1FcCjNw==
  - path: /etc/ssh/sshd_config.d/99-coder.conf
    content: |
      TrustedUserCAKeys /etc/ssh/ca_user_key.pub
  - path: /etc/profile.d/local_env.sh
    content: |
      export PATH="$PATH:~/.local/bin"
  - path: /etc/docker/daemon.json
    content: |
      {
        "data-root": "/workspace/.docker-data/"
      }
  - path: /etc/setup.sh
    encoding: b64
    content: ${base64encode(coder_agent.dev[0].init_script)}
    owner: 'root:root'
    permissions: '0755'
  - path: /etc/coder.env
    content: |
      CODER_AGENT_TOKEN=${coder_agent.dev[0].token}
      CODER_AGENT_DEVCONTAINERS_ENABLE=true
      PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:${local.home_dir}/.local/bin"
    owner: 'root:root'
  - path: /etc/systemd/system/coder-agent.service
    content: |
      [Unit]
      Description=Coder Agent
      After=network.target

      [Service]
      Type=simple
      EnvironmentFile=/etc/coder.env
      User=${local.username}
      ExecStart=/etc/setup.sh
      Restart=on-failure
      RestartSec=5s

      [Install]
      WantedBy=multi-user.target
users:
  - name: ${local.username}
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: [docker]
    shell: /bin/bash
    homedir: ${local.home_dir}
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMOTygNEK4LTfZwV1Pqf9vX5AECGXDe3paaFhiJsJvUU hulto@axe.local
runcmd:
  - ["systemctl", "daemon-reload"]
  - ["systemctl", "enable", "--now", "qemu-guest-agent.service"]
  - ["systemctl", "enable", "--now", "coder-agent.service"]
  - ["cp", "-ar", "/etc/skel/.", "${local.home_dir}"]
  - ["mkdir", "-p", "${local.home_dir}/.local/bin"]
  - ["chown", "-R", "${local.username}:${local.username}", "${local.home_dir}"]
  - ["chmod", "700", "${local.home_dir}/"]
  - ["npm", "config", "set", "-g", "prefix", "${local.home_dir}/.local/"]
EOT
  }
}

resource "harvester_cloudinit_secret" "coder-vm-init" {
  count        = data.coder_workspace.me.start_count
  name = "coder-vm-init-${local.username}-${data.coder_workspace.me.name}"
  namespace     = var.vm-namespace
  user_data     = data.cloudinit_config.startup[0].rendered
}

data "harvester_image" "vm_image" {
  name      = split("/", data.coder_parameter.os_select.value)[1]
  namespace = split("/", data.coder_parameter.os_select.value)[0]
}

resource "harvester_volume" "workspace" {
  name      = "coder-${local.username}-${data.coder_workspace.me.name}-workspace"
  namespace = var.vm-namespace
  size      = "${data.coder_parameter.disk_select.value}Gi"
}

resource "harvester_virtualmachine" "coder-vm" {
  count        = data.coder_workspace.me.start_count
  name         = "coder-${local.username}-${data.coder_workspace.me.name}"
  hostname     = "coder-${local.username}-${data.coder_workspace.me.name}"
  namespace            = var.vm-namespace
  restart_after_update = true
  cpu    = data.coder_parameter.cpu_select.value
  memory = "${data.coder_parameter.mem_select.value}Gi"

  efi         = lookup(data.harvester_image.vm_image.tags, "efi", "true") == "true" ? true : false
  secure_boot = lookup(data.harvester_image.vm_image.tags, "efi", "true") == "true" ? true : false

  run_strategy = "RerunOnFailure"
  machine_type = "q35"

  network_interface {
    name           = "nic-1"
    network_name   = local.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = "16Gi"
    bus        = "virtio"
    boot_order = 1

    image       = data.coder_parameter.os_select.value
    auto_delete = true
  }

  disk {
    name       = "workspace"
    type       = "disk"
    existing_volume_name = harvester_volume.workspace.name
    auto_delete = false
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.coder-vm-init[0].name
  }

  lifecycle {
    replace_triggered_by = [ harvester_cloudinit_secret.coder-vm-init[0].user_data ]
  }
}
