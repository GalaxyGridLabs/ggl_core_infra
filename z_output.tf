output "vault_tmp_url" {
    value = "${google_cloud_run_service.vault-core.status[0].url}"
}