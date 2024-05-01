# ====== Vault ====== 

# We'll use vault to manage a few things within the lab including
# - general secrets
# - PKI for internet facing services
# - As a OIDC provider

# Vault GCP service account
# TODO: limit this to just the vault storage bucket
resource "google_service_account" "sa-name" {
  account_id = "sa-vault-admin-storage"
  display_name = "Vault Storage Admin"
  create_ignore_already_exists = true
}

resource "google_project_iam_member" "firestore_owner_binding" {
  project = var.gcp_project
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.sa-name.email}"
}


# Vault storage container
resource "google_storage_bucket" "auto-expire" {
  name          = var.vault_storage_bucket
  location      = "US"
  force_destroy = true

  public_access_prevention = "enforced"
}



# Vault google cloud storage
# https://developer.hashicorp.com/vault/docs/configuration/storage/google-cloud-storage


# Vault cloud run container
locals {
  vault_container_name = "vault-core"
}

resource "google_cloud_run_service" "vault-core" {
  name     = "vault-core"
  location = var.gcp_region

  traffic {
    percent         = 100
    latest_revision = true
  }

  template {
    spec {
      service_account_name = google_service_account.sa-name.email
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

  depends_on = [
    google_project_service.cloud_run_api,
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