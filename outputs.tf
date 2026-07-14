output "lab_vm_summary" {
  description = "Created lab VM names and IP addresses."
  value = {
    for key, vm in module.lab_vm : key => {
      name  = vm.name
      vm_id = vm.vm_id
      ip    = vm.ip_cidr
    }
  }
}
