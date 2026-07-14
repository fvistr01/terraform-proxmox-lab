locals {
  generated_lab_vms = {
    for index in range(var.vm_count) : format("tf_lab_%02d", index + 1) => {
      vm_id       = var.vmid_start + index
      name        = format("%s-%02d", var.name_prefix, index + 1)
      ip_cidr     = format("%s/%d", cidrhost(var.lab_subnet_cidr, var.ip_start_host + index), var.lab_prefix_length)
      gateway     = var.gateway
      cores       = var.default_cores
      memory_mb   = var.default_memory_mb
      disk_gb     = var.default_disk_gb
      datastore   = var.default_datastore
      bridge      = var.default_bridge
      description = "Terraform learning VM created from cloud-init template"
    }
  }
}

module "lab_vm" {
  source = "./modules/vm"

  for_each = local.generated_lab_vms

  proxmox_node   = var.proxmox_node
  template_vm_id = var.template_vm_id
  template_node  = var.template_node

  vm_id       = each.value.vm_id
  name        = each.value.name
  description = each.value.description
  ip_cidr     = each.value.ip_cidr
  gateway     = each.value.gateway
  cores       = each.value.cores
  memory_mb   = each.value.memory_mb
  disk_gb     = each.value.disk_gb
  datastore   = each.value.datastore
  bridge      = each.value.bridge

  ssh_username   = var.ssh_username
  ssh_public_key = var.ssh_public_key
}
