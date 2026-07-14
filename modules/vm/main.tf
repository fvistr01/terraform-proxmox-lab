resource "proxmox_virtual_environment_vm" "this" {
  name        = var.name
  description = var.description
  node_name   = var.proxmox_node
  vm_id       = var.vm_id

  clone {
    vm_id        = var.template_vm_id
    node_name    = var.template_node
    datastore_id = var.datastore
    full         = true
  }

  agent {
    enabled = true
  }

  cpu {
    cores = var.cores
    type  = "host"
  }

  memory {
    dedicated = var.memory_mb
  }

  disk {
    datastore_id = var.datastore
    interface    = "scsi0"
    size         = var.disk_gb
  }

  network_device {
    bridge = var.bridge
  }

  initialization {
    datastore_id = var.datastore

    user_account {
      username = var.ssh_username
      keys     = [var.ssh_public_key]
    }

    ip_config {
      ipv4 {
        address = var.ip_cidr
        gateway = var.gateway
      }
    }
  }
}
