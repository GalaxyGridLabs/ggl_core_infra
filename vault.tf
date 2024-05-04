# ====== Vault ====== 

# We'll use vault to manage a few things within the lab including
# - general secrets
# - PKI for internet facing services
# - As a OIDC provider

# Vault GCP service account
# TODO: limit this to just the vault storage bucket
resource "google_service_account" "vault-sa" {
  account_id = "sa-vault-admin-storage"
  display_name = "Vault Storage Admin"
  create_ignore_already_exists = true
}

resource "google_project_iam_member" "vault_service" {
  project = var.gcp_project
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.vault-sa.email}"
}


# Stateful way to replace whole vault
resource "null_resource" "replace_vault_and_data" {
}


# Vault google cloud storage
# https://developer.hashicorp.com/vault/docs/configuration/storage/google-cloud-storage
resource "google_storage_bucket" "vault_storage" {
  depends_on = [null_resource.replace_vault_and_data]

  name          = var.vault_storage_bucket
  location      = "US"
  force_destroy = true

  public_access_prevention = "enforced"
}

locals {
  vault_container_name = "vault-core"
  vault_key_ring_name = "vault-keys-v2uwk"
  vault_key_name = "vault-key-dw1t1r"
}


# Vault key
# Create a KMS key ring
# terraform import google_kms_key_ring.vault_key_ring ${var.gcp_project}/${var.gcp_region}/${local.vault_key_ring_name}
# terraform import google_kms_key_ring.vault_key_ring galaxygridlabs/us-east4/vault-keys-v2uwk
resource "google_kms_key_ring" "vault_key_ring" {
   project  = "${var.gcp_project}"
   name     = "${local.vault_key_ring_name}"
   location = "${var.gcp_region}"
}


# Create a crypto key for the key ring
resource "google_kms_crypto_key" "vault_key" {
   name            = "${local.vault_key_name}"
   key_ring        = google_kms_key_ring.vault_key_ring.id
   rotation_period = "100000s"
}


resource "google_cloud_run_service" "vault-core" {
  depends_on = [
    null_resource.replace_vault_and_data,
    google_project_service.cloud_run_api
  ]

  name     = "vault-core"
  location = var.gcp_region

  traffic {
    percent         = 100
    latest_revision = true
  }

  template {
    spec {
      service_account_name = google_service_account.vault-sa.email
      containers {
        name = local.vault_container_name
        image = var.vault_container_image
        ports {
          container_port = 8200
        }

        args = ["server"]

        env {
          name = "SKIP_SETCAP"
          value = "true"
        }
        env {
          name = "VAULT_LOCAL_CONFIG"
          value = <<EOT
          ui            = true
          storage "gcs" {
            bucket = "${var.vault_storage_bucket}"
          }
          listener "tcp" {
            address       = "0.0.0.0:8200"
            tls_disable   = true
          }
          seal "gcpckms" {
            project     = "${var.gcp_project}"
            region      = "${var.gcp_region}"
            key_ring    = "${local.vault_key_ring_name}"
            crypto_key  = "${local.vault_key_name}"
          }

          EOT
        }

      }
    }

    metadata {
      annotations = {
        for k, v in {
        "autoscaling.knative.dev/minScale"      = 1
        "autoscaling.knative.dev/maxScale"      = 1
        "run.googleapis.com/client-name"        = "terraform"
        "run.googleapis.com/sessionAffinity"    = true
      }: k => v if v != ""
      }
    }
  }
  autogenerate_revision_name = true

}

# Vault-sa role bindings
resource "google_kms_key_ring_iam_binding" "vault_iam_kms_binding" {
   key_ring_id = "${google_kms_key_ring.vault_key_ring.id}"
   role = "roles/owner"

   members = [
     "serviceAccount:${google_service_account.vault-sa.email}",
   ]
}

resource "google_cloud_run_service_iam_binding" "no-auth-required" {
  location = google_cloud_run_service.vault-core.location
  service  = google_cloud_run_service.vault-core.name
  role     = "roles/run.invoker"
  
  members = [
    "allUsers"
  ]
}

# Vault DNS
data "google_dns_managed_zone" "lab-domain" {
  name = replace(var.lab_domain, ".", "-")
}

resource "google_dns_record_set" "vault-cname" {
  name = "${local.vault_fqdn}."
  type = "CNAME"
  ttl  = 300

  managed_zone = data.google_dns_managed_zone.lab-domain.name

  rrdatas = ["ghs.googlehosted.com."]
}

resource "google_cloud_run_domain_mapping" "vault-domain" {
  location = google_cloud_run_service.vault-core.location
  name     = local.vault_fqdn

  metadata {
    namespace = google_cloud_run_service.vault-core.project
  }

  spec {
    route_name = google_cloud_run_service.vault-core.name
  }
}


## PKI

## OIDC