resource "vault_policy" "admin_policy" {
  for_each = fileset("${path.module}/policies", "*.hcl")
  name   = trimsuffix(each.value, ".hcl")
  policy = file(format("%s/%s/%s", path.module, "policies", each.value))
}
