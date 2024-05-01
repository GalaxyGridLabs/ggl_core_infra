terraform {
 backend "gcs" {
   bucket  = "ggl_core_infra_mwrnmwgf6ottrmed"
   prefix  = "terraform/state"
 }
}
