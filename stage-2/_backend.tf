terraform {
 backend "gcs" {
   bucket  = "ggl_core_infra_stage2_2yh40pn8yax40w8e"
   prefix  = "terraform/state"
 }
}
