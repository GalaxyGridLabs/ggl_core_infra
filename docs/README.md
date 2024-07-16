# ggl_core_infra
Core infra to manage the Galaxy Grid homelab.

# Manual configuration
1. Create a GCP project
    1. Authenticate `gcloud` to your project
2. Register a domain `galaxygridlabs.com`
3. Create the GCP bucket backends for stage 1 and 2
    - `ggl_core_infra_stage2_2yh40pn8yax40w8e`
    - `ggl_core_infra_mwrnmwgf6ottrmed`
4. Create an oauth consent screen - https://docs.realm.pub/admin-guide/tavern
    - Create oauth consent screen
5. Import the existing key ring
```bash
terraform import google_kms_key_ring.vault_key_ring galaxygridlabs/us-east4/vault-keys-v2uwk
```
6. Generate a new key name 6 chars [a-z0-9] update the keyname
7. Run infra project once to setup vault
```
cd ./stage-1
terraform apply
```
8. Configure vault variables `VAULT_ADDR` and `VAULT_TOKEN`
9. Re-run infa project to configure vault



# Todo
- Restrict oidc to people in the GGL gcp org
    - Done with GCP Internal consent screen rn.
- Automate vault oidc
- Automate vault init and store root token in GCP secrets manager
    - Create a secret
    - Automate vault init with custom provider
    -     
- Merge stage 1 and stage 2
- Automate deployment with Github Actions
    - Create GCP service account for GH
        - Access to state bucket
        - Access to write the vault root token