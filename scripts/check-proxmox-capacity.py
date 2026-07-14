#!/usr/bin/env python3
"""
Read-only Proxmox capacity checker for Farrukh's Terraform lab.

What it does:
- SSH to the AWX jump host.
- From AWX, SSH to proxmox3.
- Query Proxmox cluster node status with pvesh.
- Query per-node storage status for the selected datastore.
- Recommend a node that has enough free RAM and disk for the requested VM.

This script does NOT create, modify, start, stop, or delete anything.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

AWX_HOST = "root@192.0.2.6"
PROXMOX_SSH = "ansible@192.0.2.133"
DEFAULT_DATASTORE = "local"
DEFAULT_AUTO_TFVARS = "generated.auto.tfvars"


@dataclass
class Candidate:
    node: str
    status: str
    cpu_pct: float
    maxcpu: int
    total_ram_gb: float
    used_ram_gb: float
    free_ram_gb: float
    datastore: str
    total_disk_gb: float | None
    used_disk_gb: float | None
    free_disk_gb: float | None
    eligible: bool
    reason: str
    score: float


def gib(value: int | float | None) -> float | None:
    if value is None:
        return None
    return float(value) / 1024 / 1024 / 1024


def run_remote(command: str) -> str:
    """Run a read-only command on proxmox3 via the AWX jump host."""
    if shutil.which("ssh") is None:
        raise SystemExit("ssh command not found")

    outer = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        AWX_HOST,
        "ssh -o BatchMode=yes -o ConnectTimeout=8 " + PROXMOX_SSH + " " + json.dumps(command),
    ]
    result = subprocess.run(outer, text=True, capture_output=True, timeout=60)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Remote command failed with exit code {result.returncode}")
    return result.stdout.strip()


def pvesh_json(path: str) -> Any:
    cmd = f"sudo -n pvesh get {path} --output-format json"
    raw = run_remote(cmd)
    return json.loads(raw)


def storage_status(node: str, datastore: str) -> dict[str, Any] | None:
    try:
        return pvesh_json(f"/nodes/{node}/storage/{datastore}/status")
    except Exception:
        return None


def build_candidates(nodes: list[dict[str, Any]], datastore: str, min_ram_gb: float, min_disk_gb: float) -> list[Candidate]:
    candidates: list[Candidate] = []

    for item in nodes:
        node = item.get("node", "unknown")
        status = item.get("status", "unknown")
        cpu_pct = float(item.get("cpu") or 0) * 100
        maxcpu = int(item.get("maxcpu") or 0)
        total_ram = gib(item.get("maxmem")) or 0
        used_ram = gib(item.get("mem")) or 0
        free_ram = max(total_ram - used_ram, 0)

        st = storage_status(node, datastore)
        total_disk = used_disk = free_disk = None
        if st:
            total_disk = gib(st.get("total"))
            used_disk = gib(st.get("used"))
            free_disk = gib(st.get("avail"))

        reasons = []
        eligible = True
        if status != "online":
            eligible = False
            reasons.append("node offline")
        if free_ram < min_ram_gb:
            eligible = False
            reasons.append(f"free RAM {free_ram:.1f} GiB < required {min_ram_gb:.1f} GiB")
        if free_disk is None:
            eligible = False
            reasons.append(f"datastore {datastore} not available/readable")
        elif free_disk < min_disk_gb:
            eligible = False
            reasons.append(f"free disk {free_disk:.1f} GiB < required {min_disk_gb:.1f} GiB")

        if not reasons:
            reasons.append("ok")

        # Simple scoring for learning:
        # prioritize free RAM, then free disk, then lower CPU usage.
        score = (free_ram * 10) + ((free_disk or 0) / 100) - cpu_pct

        candidates.append(
            Candidate(
                node=node,
                status=status,
                cpu_pct=cpu_pct,
                maxcpu=maxcpu,
                total_ram_gb=total_ram,
                used_ram_gb=used_ram,
                free_ram_gb=free_ram,
                datastore=datastore,
                total_disk_gb=total_disk,
                used_disk_gb=used_disk,
                free_disk_gb=free_disk,
                eligible=eligible,
                reason="; ".join(reasons),
                score=score,
            )
        )
    return candidates


def print_table(candidates: list[Candidate]) -> None:
    headers = [
        "Node",
        "Status",
        "CPU%",
        "Cores",
        "RAM free/total GiB",
        "Disk free/total GiB",
        "Eligible",
        "Reason",
    ]
    rows = []
    for c in candidates:
        disk_text = "n/a"
        if c.free_disk_gb is not None and c.total_disk_gb is not None:
            disk_text = f"{c.free_disk_gb:.1f}/{c.total_disk_gb:.1f}"
        rows.append(
            [
                c.node,
                c.status,
                f"{c.cpu_pct:.1f}",
                str(c.maxcpu),
                f"{c.free_ram_gb:.1f}/{c.total_ram_gb:.1f}",
                disk_text,
                "yes" if c.eligible else "no",
                c.reason,
            ]
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    print("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))


def write_auto_tfvars(path: str, best: Candidate) -> Path:
    """Write non-secret Terraform placement values for automatic loading."""
    output_path = Path(path)
    content = f'''# Generated by scripts/check-proxmox-capacity.py
# Generated at: {datetime.now().isoformat(timespec="seconds")}
# Purpose: dynamic Proxmox node placement for the Terraform learning lab.
#
# Terraform automatically loads *.auto.tfvars files in this directory.
# This file must contain only non-secret values. Do not put API tokens,
# passwords, or private keys here.

proxmox_node = "{best.node}"
'''
    output_path.write_text(content)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Proxmox node capacity checker")
    parser.add_argument("--memory-gb", type=float, default=2.0, help="Required free RAM in GiB for the new VM")
    parser.add_argument("--disk-gb", type=float, default=20.0, help="Required free disk in GiB for the new VM")
    parser.add_argument("--datastore", default=DEFAULT_DATASTORE, help="Datastore to check on each node")
    parser.add_argument(
        "--write-auto-tfvars",
        action="store_true",
        help="Write the recommended proxmox_node into generated.auto.tfvars for Terraform to auto-load",
    )
    parser.add_argument(
        "--auto-tfvars-path",
        default=DEFAULT_AUTO_TFVARS,
        help="Path for generated *.auto.tfvars output when --write-auto-tfvars is used",
    )
    args = parser.parse_args()

    print("Read-only Proxmox capacity check")
    print(f"Required VM capacity: RAM >= {args.memory_gb:.1f} GiB, disk >= {args.disk_gb:.1f} GiB")
    print(f"Datastore checked: {args.datastore}")
    print()

    nodes = pvesh_json("/nodes")
    candidates = build_candidates(nodes, args.datastore, args.memory_gb, args.disk_gb)
    candidates.sort(key=lambda c: (not c.eligible, -c.score, c.node))

    print_table(candidates)
    print()

    eligible = [c for c in candidates if c.eligible]
    if not eligible:
        print("Recommendation: no eligible node found for this VM size/datastore.")
        return 2

    best = eligible[0]
    print(f"Recommendation: use proxmox_node = \"{best.node}\"")
    print(f"Why: {best.free_ram_gb:.1f} GiB RAM free, {best.free_disk_gb:.1f} GiB datastore free, CPU currently {best.cpu_pct:.1f}%")
    if args.write_auto_tfvars:
        written = write_auto_tfvars(args.auto_tfvars_path, best)
        print()
        print(f"Wrote Terraform auto variables: {written}")
        print(f"Terraform will automatically load this file on the next plan/apply: {written.name}")
    print()
    print("Learning note:")
    print("Terraform will not make this choice by itself. This script chooses a node first; then Terraform uses that node_name.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
