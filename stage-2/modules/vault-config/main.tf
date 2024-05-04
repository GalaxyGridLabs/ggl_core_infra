output "output-json" {
    value = {
        "debug" = format("%s/%s", path.module, "policies/admin-policy.hcl")
    }  
}