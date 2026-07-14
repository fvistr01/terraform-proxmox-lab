# Terraform Proxmox Homelab Lab

This is Farrukh's Terraform learning lab on MiniBob.

Goal: practise Terraform for the Terraform Associate cert using the home Proxmox cluster.

## Current status

Done:
- Terraform installed on Mac Mini using Homebrew.
- Local project created at `/Users/xxxxxxx/homelab/terraform-proxmox-lab`.
- bpg/proxmox Terraform provider configured.
- Reusable VM module created.
- Secrets are excluded from git using `.gitignore`.

Original infrastructure setup is now done:
- Proxmox API user/token creation.
- Cloud-init template VM creation.
- Initial single-VM `terraform plan`.
- Generated fleet `terraform plan` for `vm_count = 5`.

Still approval-gated:
- `terraform apply` for creating or changing VMs.
- `terraform destroy` for removing lab VMs.

Those actions change Proxmox infrastructure and should be approved separately before we run them.

## 
1. Install Terraform locally.
2. Create Proxmox Terraform role/user/token.
3. Keep the token secret out of git.
4. Use Terraform to clone a cloud-init template.

## lab ranges

- Template VM ID: `9000`
- Terraform VM IDs: `9001-9099`
- Terraform IPs: `10.xx.xx.90-10.xx.xx.99`
- First VM: `tf-lab-01`, `10.xx.xx.91/24`

## Files

- `versions.tf`: Terraform and provider version requirements.
- `providers.tf`: Proxmox provider configuration.
- `variables.tf`: Input variables.
- `terraform.tfvars.example`: Example local variable file with placeholders.
- `main.tf`: Calls the VM module.
- `outputs.tf`: Prints VM summary.
- `modules/vm/`: Reusable VM module.

## How to use later

From the project directory:

```bash
cd /Users/xxxxxx/homelab/terraform-proxmox-lab
terraform init
terraform fmt -recursive
terraform validate
```

When Proxmox API token and template are ready:

```bash
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars and replace REPLACE_ME with your token secret
terraform plan
terraform apply
```

Destroy only lab VMs when finished:

```bash
terraform destroy
```

## Security note

Put the Proxmox token only in `terraform.tfvars` on Mac.

## Next infrastructure steps, later

1. Create Proxmox role `terraform-role`.
2. Create Proxmox user `terraform@pve`.
3. Create Proxmox API token `terraform@pve!homelab`.
4. Create cloud-init template VM ID `9000`.
5. Run `terraform plan`.
6. After review, run `terraform apply`.

## Current status - API user and template setup completed

Completed on MiniBob:

- Terraform installed and validated: v1.15.8 on darwin_arm64
- Proxmox Terraform role created: `terraform-role`
- Proxmox Terraform user created: `terraform@pve`
- API token created: `terraform@pve!homelab`
- Token secret saved locally only in `terraform.tfvars` with file mode 600
- Rocky Linux 9 GenericCloud image downloaded on `proxmox3`
- Cloud-init template created on Proxmox:
  - VMID: `9000`
  - Name: `rocky9-cloud-template`
  - Node: `proxmox3`
  - Storage: `tn-single-disk` for template disk and cloud-init drive
  - Bridge: `vmbr0`
- Terraform plan created and saved as `tf-lab-01.plan`

The current plan will create one test VM, but it has NOT been applied yet:

- Name: `tf-lab-01`
- VMID: `9001`
- IP: `192.0.2.91/24`
- Gateway: `192.0.2.1`
- CPU: 2 cores
- RAM: 2048 MB
- Disk: 20 GB
- Template clone source: VMID `9000`

Run this only after approval:

```bash
cd /Users/fvistro/homelab/terraform-proxmox-lab
terraform apply "tf-lab-01.plan"
```

## Read-only Proxmox capacity checker

A learning script was added at:

```bash
scripts/check-proxmox-capacity.py
```

It is read-only. It checks the Proxmox cluster through the AWX jump host and recommends a node based on:

- node online/offline status
- free RAM
- datastore free space
- current CPU usage

Run it like this:

```bash
cd /Users/fvistro/homelab/terraform-proxmox-lab
python3 scripts/check-proxmox-capacity.py --memory-gb 2 --disk-gb 20 --datastore tn-single-disk --write-auto-tfvars
```

Latest observed result for the first lab VM size:

```text
proxserver1: eligible, about 9.0 GiB RAM free, 917+ GiB shared datastore free
proxserver:  eligible, about 9.0 GiB RAM free, 917+ GiB shared datastore free
proxmox3:    not eligible for 2 GiB RAM request at the time checked; about 1.7 GiB RAM free

Recommendation: proxserver1
```

Learning point:

Terraform does not automatically choose the Proxmox node. The script can recommend a node first; then Terraform uses that recommendation as `proxmox_node` / `node_name`.



### Generated placement file

Run the capacity checker with `--write-auto-tfvars` to create/update `generated.auto.tfvars`. Terraform automatically loads this file. It contain only non-secret generated values such as `proxmox_node`; API tokens stay in `terraform.tfvars`.

## Current storage alignment

Before the next `terraform plan`, storage is aligned for dynamic placement:

- Template VM 9000 main disk: `tn-single-disk`
- Template VM 9000 cloud-init drive: `tn-single-disk`
- Terraform VM datastore in `terraform.tfvars`: `tn-single-disk`
- Capacity checker datastore: `tn-single-disk`
- Generated placement file: `generated.auto.tfvars` contains only `proxmox_node`

## Clone source-node fix

The template VM config for VMID `9000` lives under node `proxmox3`. Dynamic placement may choose another target node, such as `proxserver1`. For cross-node cloning with the `bpg/proxmox` provider, the VM resource must distinguish:

- `proxmox_node`: target node where the new VM is created
- `template_node`: source node where the template VM config lives

The module clone block now sets `node_name = var.template_node`, while the VM resource itself keeps `node_name = var.proxmox_node`.

## Generated 5-10 VM fleet workflow

The root Terraform config now generates the VM map automatically from a few variables instead of manually maintaining one block per VM.

Main variables in `terraform.tfvars`:

```hcl
vm_count          = 5
vmid_start        = 9001
ip_start_host     = 91
lab_subnet_cidr   = "192.0.2.0/24"
lab_prefix_length = 24
gateway           = "192.0.2.1"
name_prefix       = "tf-lab"
default_cores     = 2
default_memory_mb = 2048
default_disk_gb   = 20
default_datastore = "tn-single-disk"
default_bridge    = "vmbr0"
```

With `vm_count = 5`, Terraform declares:

```text
tf_lab_01 -> tf-lab-01 -> VMID 9001 -> 192.0.2.91/24
tf_lab_02 -> tf-lab-02 -> VMID 9002 -> 192.0.2.92/24
tf_lab_03 -> tf-lab-03 -> VMID 9003 -> 192.0.2.93/24
tf_lab_04 -> tf-lab-04 -> VMID 9004 -> 192.0.2.94/24
tf_lab_05 -> tf-lab-05 -> VMID 9005 -> 192.0.2.95/24
```

To scale to 10 VMs later, change only:

```hcl
vm_count = 10
```

That would declare VMIDs `9001-9010` and IPs `192.0.2.91-192.0.2.100`.

Safety limits:

- `vm_count` is validated to allow only `1` to `10` in this learning lab.
- `tf_lab_01` keeps the same Terraform state key as before, so the existing VM is not recreated.
- Always run `terraform plan` first and review the exact VM count before apply.
- For cloning several VMs, apply with low parallelism, for example:

```bash
terraform apply -parallelism=3 "tf-lab-fleet.plan"
```

Latest verified plan after this refactor:

```text
Plan: 4 to add, 0 to change, 0 to destroy.
```

This means the existing `tf-lab-01` is preserved and Terraform will add `tf-lab-02` through `tf-lab-05`. The plan is saved locally as `tf-lab-fleet.plan`, but it has NOT been applied.
