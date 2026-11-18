#!/usr/bin/env python3
"""Read-only Bor performance evidence. No services, databases or AWS resources are mutated."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

IMPORT = re.compile(r"Imported new chain segment\s+number=([\d,]+).*?(?:age=(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")
NUMBER = re.compile(r"Imported new chain segment\s+number=([\d,]+)")
AGE = re.compile(r"\bage=(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")
SECRET = re.compile(r"(https?://)[^\s/@]+:[^\s/@]+@", re.I)


def imported_sample(line: str, timestamp: float | None = None):
    match = NUMBER.search(line)
    if not match:
        return None
    age = AGE.search(line)
    age_seconds = None
    if age and any(x is not None for x in age.groups()):
        age_seconds = sum(int(n or 0) * scale for n, scale in zip(age.groups(), (3600, 60, 1)))
    return {"block": int(match.group(1).replace(",", "")), "age_seconds": age_seconds, "timestamp": timestamp}


def catchup(first: dict, last: dict):
    """Requires independent sample times; never confuse block height with reference head."""
    seconds = last["timestamp"] - first["timestamp"]
    delta = last["block"] - first["block"]
    if not (seconds > 0 and delta >= 0):
        return {"status": "INSUFFICIENT_EVIDENCE"}
    out = {"status": "MEASURED", "elapsed_seconds": round(seconds, 3),
           "imported_blocks": delta, "blocks_per_second": round(delta / seconds, 3)}
    if first.get("age_seconds") is not None and last.get("age_seconds") is not None:
        out["reported_age_reduction_seconds"] = first["age_seconds"] - last["age_seconds"]
    return out


def parse_diskstats(first: str, last: str, seconds: float, names: set[str]):
    """Linux /proc/diskstats fields: reads, sectors read, writes, sectors written, io ms, weighted io ms."""
    def rows(raw):
        found = {}
        for line in raw.splitlines():
            f = line.split()
            if len(f) >= 14 and f[2] in names:
                found[f[2]] = {"reads": int(f[3]), "read_sectors": int(f[5]),
                    "writes": int(f[7]), "write_sectors": int(f[9]),
                    "busy_ms": int(f[12]), "weighted_ms": int(f[13])}
        return found
    a, b = rows(first), rows(last)
    result = {}
    if seconds <= 0:
        return result
    for name in a.keys() & b.keys():
        d = {key: b[name][key] - a[name][key] for key in a[name]}
        if any(value < 0 for value in d.values()):
            continue
        result[name] = {
            "reads_per_second": round(d["reads"] / seconds, 2),
            "writes_per_second": round(d["writes"] / seconds, 2),
            "read_mib_per_second": round(d["read_sectors"] * 512 / 1048576 / seconds, 2),
            "write_mib_per_second": round(d["write_sectors"] * 512 / 1048576 / seconds, 2),
            "busy_percent": round(100 * d["busy_ms"] / (1000 * seconds), 2),
            "avg_queue_depth": round(d["weighted_ms"] / (1000 * seconds), 3),
        }
    return result


def memory_evidence(path="/sys/fs/cgroup/system.slice/bor.service"):
    base = Path(path)
    output = {}
    for filename in ("memory.current", "memory.high", "memory.max", "memory.events", "memory.pressure"):
        try:
            raw = (base / filename).read_text().strip()
            if filename == "memory.events":
                output["events"] = {k: int(v) for k, v in (x.split() for x in raw.splitlines())}
            elif filename == "memory.pressure":
                output["pressure"] = raw[:300]
            else:
                output[filename.replace(".", "_")] = raw
        except (OSError, ValueError):
            output[filename.replace(".", "_")] = None
    return output


def classify(evidence: dict):
    """Advisory triage only. Nothing here grants canonical RPC readiness."""
    reasons = []
    sync = evidence.get("catchup", {})
    if sync.get("status") != "MEASURED":
        reasons.append("CATCHUP_RATE_UNMEASURED")
    if evidence.get("readiness") != "PASS":
        reasons.append("RPC_CANONICAL_READINESS_UNPROVEN")
    for name, stats in evidence.get("disk", {}).items():
        if stats["busy_percent"] >= 85:
            reasons.append("DISK_BUSY_REVIEW:" + name)
        if stats["avg_queue_depth"] >= 4:
            reasons.append("DISK_QUEUE_REVIEW:" + name)
    events = evidence.get("memory", {}).get("events") or {}
    if events.get("oom", 0) or events.get("oom_kill", 0):
        reasons.append("MEMORY_OOM_HISTORY_REVIEW")
    return {"certification": "HOLD" if reasons else "DIAGNOSTIC_ONLY",
            "reasons": reasons, "authorizes_live": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--interval", type=float, default=15.0)
    p.add_argument("--devices", nargs="+", default=["nvme1n1", "nvme2n1"])
    p.add_argument("--readiness", default="/run/omega-polygon/readiness.json")
    p.add_argument("--journal-lines", type=int, default=300)
    args = p.parse_args()
    if not 1 <= args.interval <= 120 or not 10 <= args.journal_lines <= 2000:
        p.error("interval must be 1..120s; journal-lines 10..2000")
    before = Path("/proc/diskstats").read_text()
    first_at = time.monotonic()
    time.sleep(args.interval)
    after = Path("/proc/diskstats").read_text()
    elapsed = time.monotonic() - first_at
    journal = subprocess.run(["journalctl", "-u", "bor", "-o", "short-unix",
                              "--no-pager", "-n", str(args.journal_lines)],
                             capture_output=True, text=True, timeout=10, check=False)
    samples = []
    for line in journal.stdout.splitlines():
        try:
            ts = float(line.split()[0])
        except (ValueError, IndexError):
            continue
        point = imported_sample(line, ts)
        if point:
            samples.append(point)
    samples.sort(key=lambda x: x["timestamp"])
    rate = catchup(samples[0], samples[-1]) if len(samples) >= 2 else {"status": "INSUFFICIENT_EVIDENCE"}
    try:
        ready = json.loads(Path(args.readiness).read_text())
        age = time.time() - ready["checkedAt"]
        readiness = "PASS" if ready.get("status") == "PASS" and 0 <= age <= 30 else "FAIL"
    except (OSError, ValueError, TypeError, KeyError):
        readiness = "UNKNOWN"
    output = {"schema": "omega.node.performance.v1", "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "readiness": readiness, "catchup": rate, "disk": parse_diskstats(before, after, elapsed, set(args.devices)),
              "memory": memory_evidence(), "sample_count": len(samples)}
    output["decision"] = classify(output)
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
