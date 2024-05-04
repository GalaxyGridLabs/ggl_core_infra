# ggl_core_infra
Core infra to manage the Galaxy Grid homelab.

# Manual configuration
1. Create a GCP project
    1. Authenticate `gcloud` to your project
2. Register a domain `galaxygridlabs.com`
3. Create the GCP bucket backends for stage 1 and 2
    - `ggl_core_infra_stage2_2yh40pn8yax40w8e`
    - `ggl_core_infra_mwrnmwgf6ottrmed`
4. Import the existing key ring
```bash
terraform import google_kms_key_ring.vault_key_ring galaxygridlabs/us-east4/vault-keys-v2uwk
```
5. Generate a new key name 6 chars [a-z0-9] update the keyname
6. Run infra project once to setup vault
```
cd ./stage-1
terraform apply
```
7. Configure vault variables `VAULT_ADDR` and `VAULT_TOKEN`
8. Re-run infa project to configure vault