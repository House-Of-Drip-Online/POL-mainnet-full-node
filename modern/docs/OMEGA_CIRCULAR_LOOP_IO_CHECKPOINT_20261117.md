# Polygon 137 Native Node — Circular Readiness and RPC Output Checkpoint
**Date:** 2026-11-17. **Classification:** Read-only observed status, NOT chain-ready certification.
**Cross-system witness:** https://github.com/House-Of-Drip-Online/Apex-Omega-AWS-DOCKER/blob/main/docs/engineering/OMEGA_SYSTEM_LOOP_INPUT_OUTPUT_AUDIT_20261117.md

## Source-owned recurring cycle
Heimdall status, peers and checkpoints -> Bor syncing and peers -> independent reference latest head and same-height block-hash parity -> local state/restore/disk checks -> atomic readiness.json -> private HTTP 8545 and WS 8546 readiness admission -> CloudWatch OMEGA/PolygonNode metrics -> next monitor cycle. Authority: modern/monitor.py, modern/rpc_gate.py, modern/rpc_proxy.py, modern/rpc_ws_proxy.py.

## Required outputs per cycle
chain 137, local height/hash/timestamp, reference height/hash, comparison block/hash, lagBlocks, eth_syncing, Bor/Heimdall peer counts, disk utilization/free GiB, errors and restoration progress, gateway readiness 200/503, RPC p50/p95 by method, WS newHeads and gap recovery, source commit, independent operator attestation, timestamp and typed fail reasons. Missing measurements must not be converted to healthy zeros.

## Live audit
Read-only transport test: Bor 25/25 JSON-RPC reads returned, private HTTP gateway 0/25 successful reads (HTTP 503); measured Bor local replies were fast but stale. Later monitor reports 100 peers, lagBlocks 13097, LOCAL_HEAD_STALE, LOCAL_SYNC_INCOMPLETE, NODE_LAG_LIMIT_EXCEEDED and FAIL. No claim of canonical-ready native market data or synchronized pool state is permitted. Preserve live/recovery EBS volumes and existing rollback evidence.

## Release closure
Demonstrate 25 PASS cycles with independently matched canonical block hashes, native state reads, responsive private HTTP/WS, and reproducible downstream consumer acceptance. Source-only CI unavailable in the inspected CodeBuild account (zero queued builds permitted). No chain-data reset, stack replacement, LIVE signing or broadcast permitted by this checkpoint.
