#!/usr/bin/env python3
"""Read-only recovery triage for Polygon Bor/Heimdall-v2.

No service actions, downloads, AWS mutations, signing, or chain-state rewriting.
A recommendation is NOT an authorization to execute recovery and cannot
certify canonical state or simulated/real financial settlement.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import time

MIN_RESTORE_FREE_GIB = 200
MAX_PROGRESS_AGE_SECONDS = 180

ROUTES = (
    ("PINNED_FULL_RESTORE", "Continue the byte-identity-locked base + increment with the existing single writer"),
    ("COMPONENT_REPLAY", "Diagnose and replay only an incomplete component; retain completed-component proof"),
    ("ISOLATED_PRUNED_SNAPSHOT", "Fresh current Polygon snapshot on a separate host/volume; declare reduced historical capability"),
    ("ISOLATED_NATIVE_P2P", "Fresh Bor v2.11+ native sync from empty data directory on separate storage"),
    ("ISOLATED_EBS_RECOVERY", "Restore a consistent verified EBS snapshot onto an isolated volume, never the active Pebble writer"),
    ("EXTERNAL_RPC_CONTINUITY", "Use corroborated read-only external RPC fallback; never claim private-node readiness"),
)


def classify(*, maintenance, progress, readiness, disk, now=None):
    """Pure diagnostic; all inputs are untrusted observations."""
    now = time.time() if now is None else now
    alerts = []
    options = [{"route":route, "description":description,
                "state":"ALTERNATIVE_REQUIRES_GOVERNED_APPROVAL"} for route,description in ROUTES]
    if not isinstance(readiness, dict):
        readiness = {}
    if not isinstance(maintenance, dict):
        maintenance = {}
    if not isinstance(progress, dict):
        progress = {}

    try:
        total, free = disk.total, disk.free
        if (type(total) is not int or type(free) is not int or
                total <= 0 or free < 0 or free > total):
            raise ValueError("INVALID_DISK_OBSERVATION")
        used_pct = 100 * (1 - free / total)
        free_gib = free / (1024**3)
        if free_gib < MIN_RESTORE_FREE_GIB:
            alerts.append("RESTORE_FREE_CAPACITY_BELOW_200_GIB")
        if used_pct >= 80:
            alerts.append("DISK_USAGE_AT_OR_ABOVE_80_PERCENT")
    except (ValueError, AttributeError, TypeError):
        used_pct = None
        free_gib = None
        alerts.append("DISK_OBSERVATION_UNAVAILABLE")

    maintenance_reason = maintenance.get("reason")
    progress_state = progress.get("status")
    readiness_pass = readiness.get("status") == "PASS"
    if readiness_pass and maintenance_reason:
        alerts.append("CONTRADICTORY_READINESS_DURING_MAINTENANCE")

    age = None
    if progress_state == "RESTORING":
        t = progress.get("checkedAt")
        if type(t) in (int, float):
            age = now - t
        if age is None or not -30 <= age <= MAX_PROGRESS_AGE_SECONDS:
            alerts.append("RESTORE_PROGRESS_STALE")
        read, maximum = progress.get("compressedBytesRead"), progress.get("componentBytes")
        if type(read) is not int or type(maximum) is not int or maximum <= 0 or not 0 <= read <= maximum:
            alerts.append("RESTORE_PROGRESS_INVALID")

    if maintenance_reason not in (None, "BOR_FULL_RESTORE_PENDING"):
        alerts.append("MAINTENANCE_OWNERSHIP_CONFLICT")
        selected = "STOP_FOR_GOVERNANCE_REVIEW"
    elif progress_state == "RESTORING" and not maintenance_reason:
        alerts.append("RESTORE_RUNNING_WITHOUT_OWNED_MAINTENANCE")
        selected = "STOP_FOR_GOVERNANCE_REVIEW"
    elif progress_state == "RESTORING" and "RESTORE_PROGRESS_INVALID" in alerts:
        selected = "INVESTIGATE_RESTORE_EVIDENCE"
    elif progress_state == "RESTORING" and "RESTORE_PROGRESS_STALE" in alerts:
        selected = "INVESTIGATE_RESTORE_STALL"
    elif progress_state == "RESTORING" and free_gib is not None and free_gib < MIN_RESTORE_FREE_GIB:
        selected = "STORAGE_CAPACITY_REVIEW"
    elif progress_state == "RESTORING" and free_gib is None:
        selected = "STORAGE_TELEMETRY_REVIEW"
    elif progress_state == "RESTORING":
        selected = "PINNED_FULL_RESTORE"
        options[0]["state"] = "CONTINUE_EXISTING_WRITER_ONLY"
    elif progress_state == "RESTORED_PENDING_NATIVE_VALIDATION":
        selected = "VALIDATE_CANONICAL_BOR"
    elif readiness_pass and not maintenance_reason:
        selected = "VERIFY_CONSUMER_PATH_AND_RECOVERY_TESTS"
    elif maintenance_reason == "BOR_FULL_RESTORE_PENDING" and progress_state is None:
        alerts.append("RESTORE_PROGRESS_MISSING")
        selected = "INVESTIGATE_RESTORE_EVIDENCE"
    else:
        selected = "INVESTIGATE_NODE_WITHOUT_STARTING_ALTERNATIVE"

    if "CONTRADICTORY_READINESS_DURING_MAINTENANCE" in alerts:
        selected = "STOP_FOR_GOVERNANCE_REVIEW"

    return {
        "schema":"omega.polygon137.readonly-recovery-triage.v1",
        "observed_at_epoch":now,
        "selected":selected,
        "progress_status":progress_state,
        "maintenance_owner":maintenance_reason,
        "bor_rpc_readiness":readiness.get("status", "UNKNOWN"),
        "disk_used_percent":round(used_pct, 3) if used_pct is not None else None,
        "disk_free_gib":round(free_gib, 3) if free_gib is not None else None,
        "progress_age_seconds":round(age, 3) if age is not None else None,
        "alerts":alerts,
        "recovery_routes":options,
        "native_node_certified":False,
        "live_submission_authorized":False,
        "mutations_executed":False,
    }


def safe_load(path):
    try:
        data=json.loads(pathlib.Path(path).read_text())
        return data if isinstance(data,dict) else {}
    except (OSError, ValueError, TypeError):
        return {}



def resolve_observations(readiness, maintenance, progress, *, now):
    """Allow unprivileged operators to read a fresh, fail-closed monitor snapshot.

    The restore stage is owner-restricted. The monitor has already copied its
    read-only status into /run; never use an old snapshot or let it override a
    directly accessible source.
    """
    sources={"maintenance":"DIRECT" if maintenance else "ABSENT",
             "progress":"DIRECT" if progress else "ABSENT"}
    checked=readiness.get("checkedAt") if isinstance(readiness,dict) else None
    snapshot_current=(type(checked) in (int,float) and -10 <= now-checked <= 120
                      and readiness.get("status") == "FAIL")
    if snapshot_current:
        snapshot_maintenance=readiness.get("maintenance")
        if not maintenance and isinstance(snapshot_maintenance,dict):
            maintenance=snapshot_maintenance
            sources["maintenance"]="MONITOR_SNAPSHOT"
        snapshot_restore=readiness.get("restore")
        if not progress and isinstance(snapshot_restore,dict) and maintenance.get("reason") == "BOR_FULL_RESTORE_PENDING":
            progress=snapshot_restore
            sources["progress"]="MONITOR_SNAPSHOT"
    return maintenance,progress,sources


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--readiness",default="/run/omega-polygon/readiness.json")
    p.add_argument("--progress",default="/data/bor/full-restore/progress.json")
    p.add_argument("--maintenance",default="/etc/omega-polygon/maintenance.json")
    p.add_argument("--disk",default="/data")
    args=p.parse_args()
    try:
        disk=shutil.disk_usage(args.disk)
    except OSError:
        disk=None
    now=time.time()
    readiness=safe_load(args.readiness)
    maintenance,progress,sources=resolve_observations(
        readiness,safe_load(args.maintenance),safe_load(args.progress),now=now)
    result=classify(maintenance=maintenance,progress=progress,
                    readiness=readiness,disk=disk,now=now)
    result["evidence_sources"]=sources
    print(json.dumps(result,sort_keys=True))
    return 0 if result["selected"] in ("PINNED_FULL_RESTORE","VERIFY_CONSUMER_PATH_AND_RECOVERY_TESTS") else 2


if __name__=="__main__":
    raise SystemExit(main())
