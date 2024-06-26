resource "vault_mount" "kv-v2" {
  path = "kv-v2"
  type = "kv-v2"
}

# Enable Transit secrets engine at 'transit'
resource "vault_mount" "transit" {
  path = "transit"
  type = "transit"
}
