# Setup

1. Create a new GCP project
2. Create a GCP bucket to store the projects state.
3. Initialize the backend

```bash
$ gcloud auth application-default login
$ pulumi login gs://ggl_core_infra_vego7kei
$ pulumi stack init

```