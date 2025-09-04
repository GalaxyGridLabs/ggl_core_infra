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

variable "openai_api_key" {
  type = string
  description = "API KEy"
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
  subdomain = false
  agent_id = coder_agent.dev[0].id
}

# module "devcontainers-cli" {
#   count    = data.coder_workspace.me.start_count
#   source   = "dev.registry.coder.com/modules/devcontainers-cli/coder"
#   agent_id = coder_agent.dev[0].id
# }

# module "aider" {
#   count    = data.coder_workspace.me.start_count
#   source   = "registry.coder.com/coder/aider/coder"
#   version  = "1.1.2"
#   agent_id = coder_agent.dev[0].id
#   use_tmux    = true
#   use_screen  = false
#   ai_provider = "google"
#   ai_model    = "gemini/gemini-2.5-pro" # Uses Aider's built-in alias for gpt-4o
#   folder      = "${local.home_dir}/project"
#   ai_api_key  = var.openai_api_key
# }

module "coder-login" {
  count    = data.coder_workspace.me.start_count
  source   = "registry.coder.com/coder/coder-login/coder"
  version  = "1.1.0"
  agent_id = coder_agent.dev[0].id
}

# module "gemini" {
#   count    = data.coder_workspace.me.start_count
#   source   = "registry.coder.com/coder-labs/gemini/coder"
#   version  = "2.0.0"
#   agentapi_version = "v0.3.3"
#   agent_id = coder_agent.dev[0].id
#   gemini_api_key = var.openai_api_key
#   folder      = "${local.home_dir}/project"
# }

# module "goose" {
#   count    = data.coder_workspace.me.start_count
#   source           = "registry.coder.com/coder/goose/coder"
#   version          = "2.1.1"
#   agent_id         = coder_agent.dev[0].id
#   folder           = "${local.home_dir}/project"
#   subdomain        = false
#   install_goose    = true
#   goose_version    = "v1.0.31"
#   goose_provider   = "google"
#   goose_model      = "gemini-2.5-pro"
#   agentapi_version = "latest"
# }

# module "claude-code" {
#   count    = data.coder_workspace.me.start_count
#   source              = "registry.coder.com/coder/claude-code/coder"
#   version             = "2.2.0"
#   agent_id            = coder_agent.dev[0].id
#   folder              = "${local.home_dir}/project"
#   install_claude_code = true
#   subdomain           = false
#   claude_code_version = "latest"
# }


locals {
  oses = [
    {
      name = "Ubuntu Server 24.04 LTS (Noble)",
      value = "harvester-public/ubuntu-server-noble-24.04",
    },
  ]

  home_dir = "/home/coder"
  network_name = "harvester-public/harvester-public-net"
  username = data.coder_workspace_owner.me.name
  is_admin = contains(data.coder_workspace_owner.me.groups, "admin")
}


data "coder_parameter" "ai_prompt" {
  name = "AI Prompt"
  display_name = "AI Prompt"
  description = "Prompt for the AI companion"

  type = "string"
  form_type = "input"
  order = 1
  mutable = true
}


# resource "coder_ai_task" "aichat" {
#   count        = data.coder_workspace.me.start_count
#   sidebar_app {
#     id = coder_app.aider-chat[0].id
#   }
# }

# resource "coder_app" "gemini-chat" {
#   count        = data.coder_workspace.me.start_count
#   agent_id     = coder_agent.dev[0].id
#   slug         = "gemini-chat"
#   display_name = "Gemini Chat"
#   icon         = "${data.coder_workspace.me.access_url}/icon/gemini.svg"
#   url          = "http://localhost:3284"
#   share        = "owner"
#   subdomain    = false
#   open_in      = "tab"
#   healthcheck {
#     url       = "http://localhost:3284"
#     interval  = 5
#     threshold = 6
#   }
# }


resource "coder_script" "nightly_update" {
  count        = data.coder_workspace.me.start_count
  agent_id     = coder_agent.dev[0].id
  display_name = "Debugging"
  icon         = "/icon/database.svg"
  cron         = "* * * * * *" # Run at 22:00 (10 PM) every day
  # run_on_start = true
  script       = <<EOF
    #!/bin/sh
    touch /home/coder/win 2>&1 > /tmp/touch
  EOF
}

resource "coder_agent" "dev" {
  count        = data.coder_workspace.me.start_count
  arch = "amd64"
  os   = "linux"
  auth = "token"
  dir = local.home_dir
  connection_timeout = 480

  display_apps {
    vscode          = false
    vscode_insiders = false
    web_terminal    = true
    ssh_helper      = false
  }

  env = {
    GIT_AUTHOR_NAME     = coalesce(data.coder_workspace_owner.me.full_name, local.username)
    GIT_AUTHOR_EMAIL    = "${data.coder_workspace_owner.me.email}"
    GIT_COMMITTER_NAME  = coalesce(data.coder_workspace_owner.me.full_name, local.username)
    GIT_COMMITTER_EMAIL = "${data.coder_workspace_owner.me.email}"
    CODER_MCP_CLAUDE_SYSTEM_PROMPT = <<-EOT
      You are a helpful assistant that can help write code.
    EOT
    CODER_MCP_CLAUDE_TASK_PROMPT   = data.coder_parameter.ai_prompt.value
    CODER_MCP_CLAUDE_API_KEY = var.openai_api_key
    CODER_MCP_APP_STATUS_SLUG = "claude-code"
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
    script = "df -h --output=used,avail,pcent ${local.home_dir} | tail -1 | awk -F ' ' '{print $1 \"/\" $2 \" (\" $3 \")\" }'"
    interval = 10
    timeout = 1
  }

  metadata {
    display_name = "Root disk Usage"
    key  = "root_disk"
    script = "df -h --output=used,avail,pcent / | tail -1 | awk -F ' ' '{print $1 \"/\" $2 \" (\" $3 \")\" }'"
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
write_files:
  - path: /etc/ssh/ca_user_key.pub
    content: |
      ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCp+DQ/EFCKh7Shmo0KhbJN+WHGONDa1cAJ58WumJixrisOXN58euv69QeTMyclpPQluLchRJcIjJcfkWD7s9p5UEzHO+Gca7vaUWpeoyOl5OIWPMW47GcY3Y+H1h4g9mhIfKpbJP2OXNZNBMoSv/94vn5jvU4yAz2dyIp7Qw5Kdy1Vk/hr4kxWr3q++0xU0hOnZ0E1yG7U1ybd9XolKkUnyOGl4sxt5sgv+pQQWoSblPlqVUjaq7/WjF33fbnV2316C/MufNk0K5caAWS4lA3xiw0mF0MHhW04D64xoQvoepUP6awY0HG8LPYcTCY7hpvFNxwJoWn5UpoRaZciE2p1BxWPHqYWwTx0uhJ0MWxOLa7mkBV0c+QEyl3iNDi41gnHElW2yvb1e5GMAWdNMLF21BP8VAnba0Rt0APGNQxUAmNHsXRtF03tkhVITrKw3yEC3NIHiIVQSWJF3H+ehO1SV1n0onWqgkCawkmTe0A+gOW+5G11heEbyNtLHUmxp46wWejPrb1z86ePUgpMCAXstNPYVcxmIcEgBFW/kuxNjF6VIAMzzlHfXZdQQWOT/jAXJPBkrawjVn+DAKxxN1v3RnkK9AzIKE7olmgp8rbVXichIOZUaERfL5kRYMvQvwE4YNU6UnYEA1SexPF/PPCvTZSsrEzFLcNXMNW1FcCjNw==
  - path: /etc/ssh/sshd_config.d/99-ggl-vault.conf
    content: |
      TrustedUserCAKeys /etc/ssh/ca_user_key.pub
  - path: /etc/profile.d/local_env.sh
    content: |
      export PATH="$PATH:~/.local/bin"
  - path: /etc/docker/daemon.json
    content: |
      {
        "data-root": "${local.home_dir}/.docker-data/"
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
  - name: sysadmin
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: [docker]
    shell: /bin/bash
    homedir: /home/sysadmin
runcmd:
  - ["systemctl", "daemon-reload"]
  - ["systemctl", "enable", "--now", "qemu-guest-agent.service"]
  - ["systemctl", "enable", "--now", "coder-agent.service"]
  - ["cp", "-ar", "/etc/skel/.", "${local.home_dir}"]
  - ["mkdir", "-p", "${local.home_dir}/.local/bin", "${local.home_dir}/.local/share", "${local.home_dir}/.cache"]
  - ["git", "clone", "https://github.com/spellshift/realm.git", "${local.home_dir}/project"]
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

resource "harvester_volume" "workspace" {
  name      = "coder-${local.username}-${data.coder_workspace.me.name}-workspace"
  namespace = var.vm-namespace
  size      = "32Gi"
}

resource "harvester_virtualmachine" "coder-vm" {
  count        = data.coder_workspace.me.start_count
  name         = "coder-${local.username}-${data.coder_workspace.me.name}"
  hostname     = "coder-${local.username}-${data.coder_workspace.me.name}"
  namespace            = var.vm-namespace
  restart_after_update = true
  cpu    = 4
  memory = "8Gi"

  efi         = true
  secure_boot = true

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

    image       = "harvester-public/ubuntu-server-noble-24.04"
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
