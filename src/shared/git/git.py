import re
import pulumi

GITEA_IMAGE = "docker.io/gitea/gitea:1.22.3@sha256:76f516a1a8c27e8f8e9773639bf337c0176547a2d42a80843e3f2536787341c6"

class Gitea(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                subdomain: str,
                dns_zone: str,
                opts = None):
        
        # Set and validate inputs
        self.name = name
        self.subdomain = subdomain
        self.dns_zone = dns_zone
        super().__init__('ggl:shared/git:Gitea', name, None, opts)

    @property
    def name(self):
        return self.__name
    
    @name.setter
    def name(self, value: str):
        regex = r"[a-z0-9-]+"
        assert re.fullmatch(regex, value) is not None, f"name must match {regex}"
        self.__name = value

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
        return self.__dns_zone
    
    @dns_zone.setter
    def dns_zone(self, value: str):
        regex = r"[a-z0-9]+-[a-z]+"
        assert re.fullmatch(regex, value) is not None, f"GCP dns_zone must match {regex}"
        self.__dns_zone = value