# Setup

1. Create a new GCP project
2. Create a GCP bucket to store the projects state.
3. Initialize the backend

```bash
$ gcloud auth application-default login
$ pulumi login gs://ggl_core_infra_vego7kei
$ pulumi stack init

$ export PULUMI_CONFIG_PASSPHRASE="password"
$ PYTHONPATH=.. pulumi up --stack dev

$ pulumi config set gcp:region us-central1
$ pulumi config set gcp:zone us-central1-a
$ pulumi config set gcp:project galaxygridlabs
```


# App

```bash
$ pulumi config set vault:address https://vault.galaxygridlabs.com
$ pulumi config set vault:token hvs..... --secret

$ pulumi config set ggl:client_id 1051431507099-i2d83aiogb0c349go9si6j8ahuv5p6ml.apps.googleusercontent.com
$ pulumi config set ggl:client_secret ... --secret
$ pulumi config set ggl:vault_sa_account_json '{...json...}' --secret
$ pulumi config set ggl:gsuite_admin 'sysadmin [@] hul.to'
$ pulumi config set ggl:gsuite_domain 'hul.to'
```

## Restore gitea from snapshot backup
```bash
# Get the instance ID
gcloud compute instances list
NAME
gitea-1332bb9

instance="gitea-1332bb9"

# Get the existing disk ID
gcloud compute disks list
NAME           LOCATION       LOCATION_SCOPE  SIZE_GB  TYPE         STATUS
gitea-1332bb9  us-central1-a  zone            10       pd-standard  READY
gitea-5249582  us-central1-a  zone            16       pd-standard  READY

# The data disk is 16GB and the boot disk is 10
old_disk="gitea-5249582"

# Create a new disk from snapshot
gcloud compute snapshots list
NAME                                                 DISK_SIZE_GB  SRC_DISK                           STATUS
gitea-5249582-us-central1-a-20241111090803-87j8fei3  16            us-central1-a/disks/gitea-5249582  READY

gcloud compute snapshots describe gitea-5249582-us-central1-a-20241111090803-87j8fei3
snapshot="gitea-5249582-us-central1-a-20241111090803-87j8fei3"

# Get resource policy so we can attach it to the new disk
gcloud compute resource-policies list
NAME                DESCRIPTION                                 REGION                                                                             CREATION_TIMESTAMP
default-schedule-1                                              https://www.googleapis.com/compute/v1/projects/galaxygridlabs/regions/us-central1  2024-08-26T15:06:09.170-07:00
gitea-0b3be8b       Create backups of the Gitea data partition  https://www.googleapis.com/compute/v1/projects/galaxygridlabs/regions/us-central1  2024-11-09T13:50:44.521-08:00

resource_policies="gitea-0b3be8b"

# Generate unique ID and disk
new_disk="gitea-$(hexdump -vn4 -e'"%06x" 1 "\n"' /dev/urandom)"

gcloud compute disks create $new_disk \
    --size=16 \
    --source-snapshot=$snapshot \
    --resource-policies=$resource_policies \
    --type=pd-standard

# Detach the old disk
gcloud compute instances detach-disk $instance --disk=$old_disk

# Import the new disk to pulumi
cd src/2_app
pulumi stack --show-urns --show-ids
    TYPE                                             NAME
    pulumi:pulumi:Stack                              2_app-dev
    │  URN: urn:pulumi:dev::2_app::pulumi:pulumi:Stack::2_app-dev
    ├─ ggl:shared/git:Gitea                          gitea
    │  │  URN: urn:pulumi:dev::2_app::ggl:shared/git:Gitea::gitea
    │  ├─ gcp:compute/disk:Disk                      gitea
    │  │     URN: urn:pulumi:dev::2_app::ggl:shared/git:Gitea$gcp:compute/disk:Disk::gitea
    │  │     ID: projects/galaxygridlabs/zones/us-central1-a/disks/gitea-5249582

# delete the disk, instance, and record set
pulumi state delete 'urn:pulumi:dev::2_app::ggl:shared/git:Gitea$gcp:compute/disk:Disk::gitea' --force --target-dependents

# Import the backup disk
pulumi import gcp:compute/disk:Disk gitea $new_disk --parent 'urn:pulumi:dev::2_app::ggl:shared/git:Gitea::gitea'
PYTHONPATH=.. pulumi up --stack dev

# Cleanup old instance
gcloud compute instances delete $instance
```