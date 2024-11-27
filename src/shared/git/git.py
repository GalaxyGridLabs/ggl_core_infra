import re
import pulumi
import pulumi_gcp as gcp
import pulumi_random as prandom

GITEA_IMAGE = "docker.io/gitea/gitea:1.22.3@sha256:76f516a1a8c27e8f8e9773639bf337c0176547a2d42a80843e3f2536787341c6"
GITEA_DISK_SIZE = 16
GITEA_MACHINE_TYPE = "f1-micro"
GITEA_PORT = 3000
GITEA_TLS_PORT = 443
GITEA_SSH_PORT = 2222

CADDY_IMAGE = "docker.io/library/caddy:2.9-alpine@sha256:9cc41f26f734861421d99f00fc962b3a3181aab9b4dbd0ac7751a883623794b6"

COS_IMAGE = "projects/cos-cloud/global/images/cos-stable-113-18244-151-9"
COS_DISK_SIZE = 10

class Gitea(pulumi.ComponentResource):
    def __init__(self,
                name: str,
                subdomain: str,
                dns_zone: str,
                tls_cert,
                tls_key,
                opts = None):
        
        # Set and validate inputs
        self.name = name
        self.subdomain = subdomain
        self.dns_zone = dns_zone
        super().__init__('ggl:shared/git:Gitea', name, None, opts)

        env_dns_zone = gcp.dns.get_managed_zone(
            name=self.dns_zone)

        fqdn = f"{self.subdomain}.{env_dns_zone.dns_name}".removesuffix(".")


        # Create backup policy
        snapshot_policy = gcp.compute.ResourcePolicy(
            resource_name=name,
            description="Create backups of the Gitea data partition",
            snapshot_schedule_policy={
                "schedule": {
                    "weekly_schedule": {
                        "day_of_weeks": [{
                            "day": "MONDAY",
                            "start_time": "09:00",
                        },{
                            "day": "THURSDAY",
                            "start_time": "09:00",
                        }],
                    },
                },
                "retention_policy": {
                    "max_retention_days": 21,
                    "on_source_disk_delete": "APPLY_RETENTION_POLICY",
                },
            },
            opts=pulumi.ResourceOptions(parent=self))

        # Create a data disk
        data = gcp.compute.Disk(
            resource_name=name,
            type="pd-standard",
            size=GITEA_DISK_SIZE,
            resource_policies=[snapshot_policy],
            opts=pulumi.ResourceOptions(
                parent=self, 
                protect=True,
                ignore_changes=["snapshot"], # Ignore changes to snapshot source so we can restore from backup
                ))

        # Setup FW rules
        git_tag = prandom.RandomId(
            resource_name=name,
            prefix=f"{name}-",
            byte_length=3,
            opts=pulumi.ResourceOptions(parent=self))
        git_fw = gcp.compute.Firewall(
            resource_name=name,
            network="default",
            allows=[
                {
                    "protocol": "tcp",
                    "ports": [
                        GITEA_SSH_PORT,
                        GITEA_TLS_PORT,
                    ],
                },
            ],
            target_tags=[git_tag.hex],
            source_ranges=["0.0.0.0/0"],
            opts=pulumi.ResourceOptions(parent=self))

        # Setup Caddy https reverse proxy 443 -TLS-> 3000
        def generate_user_data(cert: str, key: str):
          # Fix YAML indentation
          cert = cert.replace("\n", "\n      ")
          key = key.replace("\n", "\n      ")
          return f"""#cloud-config

write_files:
- path: /etc/systemd/system/caddy.service
  owner: root:root
  permissions: '0755'
  content: |
      [Unit]
      Description=Startup caddy container
      Requires=docker.service
      After=docker.service

      [Service]
      Type=simple
      ExecStart=/usr/bin/docker run -p 443:443 -v /var/caddy/:/data:ro --add-host=host.docker.internal:host-gateway --name caddy {CADDY_IMAGE} caddy run --config /data/Caddyfile --adapter caddyfile
      Restart=always
      RestartSec=30

      [Install]
      WantedBy=multi-user.target
- path: /var/caddy/Caddyfile
  owner: root:root
  permissions: '0755'
  content: |
      {fqdn} {{
        tls /data/certs/cert.pem /data/certs/key.pem
        reverse_proxy host.docker.internal:{GITEA_PORT}
      }}
- path: /var/caddy/certs/cert.pem
  owner: root:root
  permissions: '0755'
  content: |
      {cert}
- path: /var/caddy/certs/key.pem
  owner: root:root
  permissions: '0755'
  content: |
      {key}
runcmd:
  - systemctl daemon-reload
  - systemctl enable --now caddy
"""
        
        """
        - path: /var/caddy/certs/key.pem
  owner: root:root
  permissions: '0755'
  content: |
      {key}
"""
        
        user_data = pulumi.Output.all(
            tls_cert=tls_cert,
            tls_key=tls_key,
            ).apply(lambda args: generate_user_data(cert=args["tls_cert"], key=args["tls_key"])) 

        

        # Create a COS spec
        def generate_spec(pd_name: str):
            return f"""
spec:
  containers:
  - name: {name}
    image: {GITEA_IMAGE}
    env:
    - name: DISABLE_REGISTRATION
      value: 'true'
    - name: GITEA__openid__ENABLE_OPENID_SIGNIN
      vaule: 'true'
    - name: GITEA__openid__ENABLE_OPENID_SIGNUP
      value: 'true'
    - name: GITEA__oauth2_client__ENABLE_AUTO_REGISTRATION
      value: 'true'
    - name: GITEA__oauth2_client__ACCOUNT_LINKING
      value: 'auto'
    - name: GITEA__oauth2_client__OPENID_CONNECT_SCOPES
      value: gitea-auth openid
    - name: GITEA__server__ROOT_URL
      value: https://{fqdn}/
    - name: USER_UID
      value: '1000'
    - name: USER_GID
      value: '1000'
    - name: GITEA__server__HTTP_PORT
      value: {GITEA_PORT}
    - name: SSH_PORT
      value: {GITEA_SSH_PORT}
    - name: SSH_LISTEN_PORT
      value: {GITEA_SSH_PORT}
    - name: GITEA__database__DB_TYPE
      value: sqlite3
    - name: GITEA__database__PATH
      value: /data/gitea/gitea.db
    volumeMounts:
    - name: pd-0
      readOnly: false
      mountPath: /data
    stdin: false
    tty: false
  volumes:
  - name: pd-0
    gcePersistentDisk:
      pdName: {pd_name}
      fsType: ext4
      partition: 0
      readOnly: false
"""
        spec_str = pulumi.Output.all(
            pd_name=data.name
            ).apply(lambda args: generate_spec(args["pd_name"])) 
        

        # Deploy COS instance
        cos_instance = gcp.compute.Instance(
            resource_name=name,
            machine_type=GITEA_MACHINE_TYPE,
            boot_disk={
                "initialize_params": {
                    "image": COS_IMAGE,
                    "size": COS_DISK_SIZE,
                    "type": "pd-standard"
                }
            },
            attached_disks=[{
                    "device_name": data.name,
                    "mode": "READ_WRITE",
                    "source": data.name
                }],
            tags=[git_tag.hex],
            network_interfaces=[{
                    "access_configs": [{
                        "nat_ip": "",
                        "network_tier": "STANDARD",
                    }],
                    "subnetwork": "default",
                    "stack_type": "IPV4_ONLY",
                }],
            service_account={
                "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
            },
            allow_stopping_for_update=True,
            metadata={
                "gce-container-declaration": spec_str,
                "google-logging-enabled": True,
                "user-data": user_data,
            },
            # metadata_startup_script=startup_file,
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
                replace_on_changes=["metadata"],
                ))

        self.ip_addr = cos_instance.network_interfaces[0].apply(lambda iface: iface.access_configs[0].nat_ip)
        
        dns = gcp.dns.RecordSet(
            resource_name=name,
            name=f"{self.subdomain}.{env_dns_zone.dns_name}",
            type="A",
            ttl=300,
            managed_zone=env_dns_zone.name,
            rrdatas=[self.ip_addr],
            opts=pulumi.ResourceOptions(parent=self))

        self.url = dns.name.apply(lambda domain: f"https://{domain.removesuffix('.')}/")


        """
        Might be automatable - https://docs.gitea.com/next/administration/command-line
        - This is doable but seems messy would require:
          - Mounting in a small `app.ini`
          - Fixing missing vars that /etc/s6/gitea/setup creates
          - Starting the app with entrypoint
          - Running the `gtiea admin auth add-oauth --provider openidConnect` command

        This doesn't seem worthwhile given git won't be going up and down that often.

        Manual configuration:
        1. Navigate to `gitea.url`
        2. Create admin user `root`
        3. Setup auth method
        Icon URL - https://www.datocms-assets.com/2885/1676497447-vault-favicon-color.png?h=32&w=32
        OpenID Connect Auto Discovery URL - https://vault.galaxygridlabs.com/v1/identity/oidc/provider/gitea-auth/.well-known/openid-configuration
        Additional Scopes - gitea-auth openid profile email
        Claim name providing group names for this source. (Optional) - groups
        Group Claim value for administrator users. (Optional - requires claim name above) - labadmins@hul.to
        Map claimed groups to Organization teams. (Optional - requires claim name above) - {"red-team@hul.to":{"red-team":["red-teamers"]}}

        4. Login with OIDC
        5. Disable root user
        """

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