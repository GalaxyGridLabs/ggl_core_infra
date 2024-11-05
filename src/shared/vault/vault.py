from dataclasses import dataclass
import re

class Vault:
    def __init__(self,
                subdomain: str,
                dns_zone: str):
        
        self.subdomain = subdomain
        self.dns_zone = dns_zone

        return
    
        # Set Vault DNS CNAME to `ghs.googlehosted.com.`

        # New kms KeyRing

        # New kms Key

        # New service account

        # Set SA permissions

        # New bucket

        # Generate config

        # Create cloud run service

        # IAM binding allow all to access vault

        # Domain mapping for vault

        # Use private domain and custom curl to init vault

        # Store public url, and root_token

        return
    
    @property
    def subdomain(self):
        return self.__subdomain
    
    @subdomain.setter
    def subdomain(self, value: str):
        regex = r"[a-z0-9-]+"
        assert re.fullmatch(regex, value) is not None, f"subdomain must match {regex}"
        self.__subdomain = value

    @property
    def dns_zone(self):
        return self.__subdomain
    
    @dns_zone.setter
    def dns_zone(self, value: str):
        regex = r"[a-z0-9]+-[a-z]+"
        assert re.fullmatch(regex, value) is not None, f"GCP dns_zone must match {regex}"
        self.__dns_zone = value