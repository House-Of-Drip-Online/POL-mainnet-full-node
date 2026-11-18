#!/usr/bin/env python3
"""Read-only, evidence-preserving native Polygon node certification sampler.

This CLI probes real local/reference Polygon RPCs and the private gateway.
Unit-test fixtures may inject a query function, but production observations
are NEVER replaced with mock state. Results do not authorize trading.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from rpc_gate import evaluate_rpc_gate, rpc_query, height, read_head


def _timed(query, url: str, method: str, params: list, timeout: float):
    started = time.perf_counter()
    try:
        result = query(url, method, params, timeout)
        return result, round((time.perf_counter() - started) * 1000, 3), None
    except Exception as exc:
        # Never interpolate remote exception text: it may reveal URL/API keys.
        return None, round((time.perf_counter() - started) * 1000, 3), (
            "HTTP_" + str(exc.code) if isinstance(exc, urllib.error.HTTPError)
            else "RPC_RESPONSE_UNAVAILABLE"
        )


def sample_native_cycle(
    local_url: str, reference_url: str, gateway_url: str, *,
    query=rpc_query, now_seconds: float | None = None,
):
    now = time.time() if now_seconds is None else now_seconds
    chain, chain_ms, chain_error = _timed(query, local_url, "eth_chainId", [], 4)
    sync, sync_ms, sync_error = _timed(query, local_url, "eth_syncing", [], 4)
    peers, peers_ms, peers_error = _timed(query, local_url, "net_peerCount", [], 4)
    head, head_ms, head_error = _timed(query, local_url, "eth_getBlockByNumber", ["latest", False], 4)
    gateway, gateway_ms, gateway_error = _timed(query, gateway_url, "eth_chainId", [], 4)

    failures = [k for k, v in (
        ("LOCAL_CHAIN_UNAVAILABLE", chain_error),
        ("LOCAL_SYNC_UNAVAILABLE", sync_error),
        ("LOCAL_PEERS_UNAVAILABLE", peers_error),
        ("LOCAL_HEAD_UNAVAILABLE", head_error),
        ("PRIVATE_GATEWAY_" + (gateway_error or "UNAVAILABLE"), gateway_error),
    ) if v]
    node_head = None
    native_peers = None
    try:
        if height(chain) != 137:
            failures.append("LOCAL_CHAIN_ID_MISMATCH")
        node_head = read_head(head)
        native_peers = height(peers)
        if native_peers < 1:
            failures.append("LOCAL_PEERS_ZERO")
    except (TypeError, ValueError):
        failures.append("LOCAL_RESPONSE_INVALID")
    if sync is not False:
        failures.append("LOCAL_SYNC_INCOMPLETE")
    if gateway_error is None and gateway != "0x89":
        failures.append("GATEWAY_CHAIN_INVALID")

    # Independently match actual canonical header hashes at the common block.
    # This gate remains FAIL on missing reference evidence, stale heads, or
    # mismatched hashes. Never infer readiness from a fast local RPC.
    gate = evaluate_rpc_gate(local_url, reference_url,
                             now_seconds=now, timeout_seconds=4, query=query)
    failures.extend(gate.get("failures", []))
    ready = not failures and gate.get("status") == "PASS"
    return {
        "schema": "omega.polygon137.native-cycle-witness.v1",
        "status": "PASS" if ready else "FAIL",
        "executionAuthorized": False,
        "observedAtUnixMs": int(now * 1000),
        "sourceChainId": 137 if chain == "0x89" else None,
        "localHead": node_head,
        "borPeers": native_peers,
        "borSyncing": sync is not False if sync_error is None else None,
        "gatewayReady": gateway_error is None and gateway == "0x89",
        "gatewayFailure": gateway_error,
        "canonicalComparisonBlock": gate.get("canonicalComparisonBlock"),
        "lagBlocks": gate.get("lagBlocks"),
        "rpcLatencyMs": {
            "chainId": chain_ms, "syncing": sync_ms, "peers": peers_ms,
            "head": head_ms, "gateway": gateway_ms,
        },
        "failures": sorted(set(failures)),
    }


def _p95(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, (95 * len(ordered) + 99) // 100 - 1)]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only native Polygon 25-cycle diagnostic; not a trading certification")
    parser.add_argument("--settings", default="/etc/omega-polygon/settings.json")
    parser.add_argument("--local-url", default="http://127.0.0.1:18545")
    parser.add_argument("--gateway-url", default="http://10.77.1.77:8545")
    parser.add_argument("--cycles", type=int, default=25)
    parser.add_argument("--interval-seconds", type=float, default=2)
    args = parser.parse_args(argv)
    if not 1 <= args.cycles <= 100 or not 0 <= args.interval_seconds <= 120:
        parser.error("cycles must be 1..100 and interval 0..120 seconds")
    settings = json.loads(pathlib.Path(args.settings).read_text())
    reference = settings.get("referenceUrl")
    if not isinstance(reference, str) or not reference.startswith(("http://", "https://")):
        raise SystemExit("REFERENCE_RPC_NOT_CONFIGURED")

    samples = []
    for i in range(args.cycles):
        row = sample_native_cycle(args.local_url, reference, args.gateway_url)
        row["cycleNumber"] = i + 1
        print(json.dumps(row, sort_keys=True), flush=True)
        samples.append(row)
        if i + 1 < args.cycles:
            time.sleep(args.interval_seconds)
    latencies = [v for s in samples for k, v in s["rpcLatencyMs"].items()
                 if k != "gateway" and isinstance(v, (int, float))]
    summary = {
        "schema": "omega.polygon137.native-25-summary.v1",
        "cycles": len(samples),
        "passCount": sum(s["status"] == "PASS" for s in samples),
        "failCount": sum(s["status"] != "PASS" for s in samples),
        "nativeRpcP50Ms": statistics.median(latencies) if latencies else None,
        "nativeRpcP95Ms": _p95(latencies),
        "initialBlock": samples[0]["localHead"]["height"] if samples[0]["localHead"] else None,
        "finalBlock": samples[-1]["localHead"]["height"] if samples[-1]["localHead"] else None,
        "allPassed": all(s["status"] == "PASS" for s in samples),
        "economicCertification": "NOT_EVALUATED",
        "consumerAcknowledgments": "NOT_EVALUATED",
        "executionAuthorized": False,
    }
    print(json.dumps({"summary": summary}, sort_keys=True), flush=True)
    return 0 if summary["allPassed"] else 2


if __name__ == "__main__":
    sys.exit(main())
