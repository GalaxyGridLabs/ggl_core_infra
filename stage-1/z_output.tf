output "stage-2-setup" {
    value = <<EOT
export VAULT_ADDR="${google_cloud_run_service.vault-core.status[0].url}"
vault operator init
# Copy the root token
export VAULT_TOKEN="hvs...."
EOT
}