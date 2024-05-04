# ========= Must set =========
variable "gcp_project" {
  type = string
  description = "GCP Project ID for deployment"
  validation {
    condition = length(var.gcp_project) > 0
    error_message = "Must provide a valid gcp_project"
  }
}

variable "lab_domain" {
  type = string
  description = "The domain the lab should use"
  validation {
    condition = can(regex("^[a-z-].+[.][a-z].+$", var.lab_domain))
    error_message = "Invalid domain expected domain in the format `example.com`."
  }
}

# ========= Can set ============
variable "vault_sub_domain" {
  type = string
  description = "The subdomain that vault should exist at"
  default = "vault"
  validation {
    condition = can(regex("^[a-z-].+$", var.vault_sub_domain))
    error_message = "Invalid domain expected sub-domain in the format `subdomain`."
  }
}

# ========= Don't change ===========

variable "gcp_region" {
  type = string
  description = "GCP Region for deployment"
  default = "us-east4"
}

variable "vault_container_image" {
  type = string
  description = "The vault container image to use"
  default = "docker.io/hashicorp/vault:1.16.2@sha256:e139ff28c23e1f22a6e325696318141259b177097d8e238a3a4c5b84862fadd8"
}

variable "vault_storage_bucket" {
  type = string
  description = "The bucket to store vault data in"
  default = "ggl_vault_storage_klfpagke8nvjcjla"
}

# ========= Generated =========
locals {
  vault_fqdn = "${var.vault_sub_domain}.${var.lab_domain}"
}