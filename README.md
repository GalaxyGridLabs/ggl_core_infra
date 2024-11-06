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
```