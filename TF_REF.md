```terraform
# This code is compatible with Terraform 4.25.0 and versions that are backwards compatible to 4.25.0.
# For information about validating this Terraform code, see https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/google-cloud-platform-build#format-and-validate-the-configuration

resource "google_compute_instance" "instance-20240826-221941" {
  attached_disk {
    device_name = "giteadata"
    mode        = "READ_WRITE"
    source      = "projects/galaxygridlabs/zones/us-central1-a/disks/disk-1"
  }

  boot_disk {
    auto_delete = true
    device_name = "instance-20240826-221941"

    initialize_params {
      image = "projects/cos-cloud/global/images/cos-stable-113-18244-151-23"
      size  = 10
      type  = "pd-balanced"
    }

    mode = "READ_WRITE"
  }

  can_ip_forward      = false
  deletion_protection = false
  enable_display      = false

  labels = {
    container-vm = "cos-stable-113-18244-151-23"
    goog-ec-src  = "vm_add-tf"
  }

  machine_type = "e2-medium"

  metadata = {
    gce-container-declaration = "spec:\n  containers:\n  - name: instance-20240826-221941\n    image: test123\n    volumeMounts:\n    - name: pd-0\n      readOnly: false\n      mountPath: /var/gitea/data\n    stdin: false\n    tty: false\n  volumes:\n  - name: pd-0\n    gcePersistentDisk:\n      pdName: giteadata\n      fsType: ext4\n      partition: 0\n      readOnly: false\n  restartPolicy: Always\n# This container declaration format is not public API and may change without notice. Please\n# use gcloud command-line tool or Google Cloud Console to run Containers on Google Compute Engine."
  }

  name = "instance-20240826-221941"

  network_interface {
    access_config {
      network_tier = "PREMIUM"
    }

    queue_count = 0
    stack_type  = "IPV4_ONLY"
    subnetwork  = "projects/galaxygridlabs/regions/us-central1/subnetworks/default"
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
    provisioning_model  = "STANDARD"
  }

  service_account {
    email  = "1051431507099-compute@developer.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/service.management.readonly", "https://www.googleapis.com/auth/servicecontrol", "https://www.googleapis.com/auth/trace.append"]
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = false
    enable_vtpm                 = true
  }

  zone = "us-central1-a"
}
```
