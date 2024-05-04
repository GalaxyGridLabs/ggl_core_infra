module "vault-config" {
    source = "./modules/vault-config"
}



output "output-json" {
    value = module.vault-config.output-json
}