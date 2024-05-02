# ====== GCP VPC ======
# Is this needed?a



# ====== Lab DNS ====== 

# The services within the lab will have unknown IP addresses.
# Instead of trying to build a resource, get an ip, and share
# that backwards to the Terraform we'll instead precompute
# a domain name and have all components reference that.
# In order to ensure programatic access I need a DNS server
# that will update quickly.

# - GCP Interal - fast but requires you to be on the GCP VPC
# - Netmaker - fast but unknown and requires you to be connected to netmaker
# - Real DNS - Can be slow to propegate - may just need to force TF to wait.

