# Polygon 137 — Native 25-Cycle Read-Only Witness

Run after code review on the authorized node host using the existing private settings file:

```sh
python3 modern/probes/native_25_cycle_cert.py --settings /etc/omega-polygon/settings.json --cycles 25 --interval-seconds 2
```

Inputs must include the real local Bor HTTP listener at `127.0.0.1:18545`, an independently operated reference RPC from node settings, and the private gateway `10.77.1.77:8545`. Do not print API-key-bearing reference URLs.

Each result preserves chain ID, local block number/hash/time, Bor peer count and sync status, measured RPC latencies, independent pinned-header parity, reference lag and gateway response, with typed failures. A PASS requires canonical freshness, sync completion and a working private gateway. The summary records all cycle dispositions and measured latency percentiles. All observations are read-only, never signs, never transmits.

This witness covers node N1–N4 and HTTP gateway readiness. It does **not** prove WSS subscriptions, actual pool reserve freshness, Asset Hunter signed publication, APEX/SYMEN ACK, native quote, fork simulation, positive net economics or full end-to-end SHADOW certification. None of these fields may be inferred from a node PASS. Fixtures in unit tests cannot be used as live market evidence.

Current production Bor is still synchronizing and the gateway remains fail-closed. Never loosen the native readiness gate or reset persistent chain data to make this probe pass.
