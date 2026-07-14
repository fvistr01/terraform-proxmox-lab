variable "proxmox_endpoint" {
  description = "Proxmox API endpoint, for example https://192.0.2.133:8006/api2/json"
  type        = string
}

variable "proxmox_api_token" {
  description = "Proxmox API token in bpg provider format: terraform@pve!homelab=TOKEN_VALUE"
  type        = string
  sensitive   = true
}

variable "proxmox_node" {
  description = "Target Proxmox node name. This is generated dynamically in generated.auto.tfvars by the capacity checker."
  type        = string
  default     = "proxmox3"
}

variable "template_node" {
  description = "Proxmox node where the source template VM config lives. Template VM 9000 currently lives on proxmox3."
  type        = string
  default     = "proxmox3"
}

variable "template_vm_id" {
  description = "Cloud-init template VM ID to clone from."
  type        = number
  default     = 9000
}

variable "vm_count" {
  description = "Number of lab VMs to create from the template. Keep this between 1 and 10 for this learning lab."
  type        = number
  default     = 1

  validation {
    condition     = var.vm_count >= 1 && var.vm_count <= 10
    error_message = "vm_count must be between 1 and 10 for this lab. Increase deliberately only after capacity/IP checks."
  }
}

variable "vmid_start" {
  description = "First Proxmox VM ID for generated lab VMs. VM 1 uses this ID, VM 2 uses this ID + 1, and so on."
  type        = number
  default     = 9001
}

variable "ip_start_host" {
  description = "First host number inside lab_subnet_cidr. With 192.0.2.0/24 and 91, VM 1 gets 192.0.2.91."
  type        = number
  default     = 91
}

variable "lab_subnet_cidr" {
  description = "Subnet used to calculate generated VM IP addresses."
  type        = string
  default     = "192.0.2.0/24"
}

variable "lab_prefix_length" {
  description = "Prefix length appended to generated VM IP addresses."
  type        = number
  default     = 24
}

variable "gateway" {
  description = "Default gateway for generated lab VMs."
  type        = string
  default     = "192.0.2.1"
}

variable "name_prefix" {
  description = "Prefix for generated VM names."
  type        = string
  default     = "tf-lab"
}

variable "default_cores" {
  description = "CPU cores per generated lab VM."
  type        = number
  default     = 2
}

variable "default_memory_mb" {
  description = "Memory in MB per generated lab VM."
  type        = number
  default     = 2048
}

variable "default_disk_gb" {
  description = "Disk size in GB per generated lab VM."
  type        = number
  default     = 20
}

variable "default_datastore" {
  description = "Datastore for generated lab VM disks and cloud-init data."
  type        = string
  default     = "tn-single-disk"
}

variable "default_bridge" {
  description = "Network bridge for generated lab VMs."
  type        = string
  default     = "vmbr0"
}

variable "ssh_username" {
  description = "Linux user cloud-init should create/use in the VM."
  type        = string
  default     = "fvistro"
}

variable "ssh_public_key" {
  description = "Public SSH key injected by cloud-init."
  type        = string
}
