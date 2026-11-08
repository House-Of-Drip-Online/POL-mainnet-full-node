# Polygon Node Two-Repository Compatibility and Reuse Disposition

**Evaluated:** 2026-11-08, Polygon PoS mainnet 137.
**Scope:** `House-Of-Drip-Online/POL-mainnet-full-node` and `House-Of-Drip-Online/dappnode-polygon`. Evaluated GitHub source and actual node host `i-0e9c908e9994086e8`, not just package descriptions.

| DAppNode feature / issue | Exact legacy source | Canonical 2026 host finding | Final disposition |
| --- | --- | --- | --- |
| Bor client | `build/bor/Dockerfile` plus `docker-compose.yml` uses `v0.2.14-tmp-span-hotfix` | `/usr/bin/bor version` returned `2.11.0` | **REJECT** legacy binary. Public Uburu mainnet fork active since Nov 5, 2026; older clients cannot follow |
| Heimdall | `v0.2.8` old Heimdall v1 via Docker build | `heimdalld 0.13.2`, `heimdallv2-137` actively syncing, 27 peers at sample | **REJECT** Heimdall v1 |
| Snapshot | `wget -c $SNAPSHOT_URL -O - | tar -xz` against March 2022 files | Byte-pinned HTTP ranges, SHA256 component digest, LZ4 and protected staging | **REJECT** old snapshots and unverified extraction |
| Message bus / REST | RabbitMQ and a second Heimdall REST container | Heimdall v2 REST at local `127.0.0.1:1317`; RabbitMQ and Docker inactive | **NOT NEEDED**; no retrofitted AMQP dependency |
| Bor peer ceiling | `--maxpeers=${MAXPEERS:-200}` | Configured `p2p.maxpeers=100`; Bor offline pending guarded restore | **OPTIONAL AFTER SYNC**. Benchmark 100 vs 150 vs 200 while preserving node CPU, network and peer quality; do not increase blindly |
| Txpool endpoints | HTTP namespace `txpool`, 131072 slots | Private read-only gateway explicitly excludes `txpool`; pending-transaction WS subscriptions denied | **DO NOT EXPOSE**. Separate audited local observability only if justified by measurable requirements |
| HTTP security | `--http.addr=0.0.0.0`, wildcard CORS/vhosts; WS wildcard | Loopback Bor privileged port `18545`; private bounded read gateway `8545`, denied broadcasts | **REJECT** DAppNode exposure settings |
| Operator configuration | `setup-wizard.yml` | CLI/CloudFormation, no DAppNode agent | **TRANSLATE CONCEPT ONLY**. Legacy wizard misspells `MONIKER` as `MONKIER` and is not a valid current host authority |
| Recovery automation | Docker restart and boot marker | systemd maintenance owner, guarded single-writer full restore, fail-closed gateway | **KEEP NEW**; use `modern/recovery_advisor.py` for *read-only* six-route triage |
| Backups | Empty `backup: []` package manifest | AWS DLM daily backups enabled, one completed snapshot observed | **KEEP NEW**. Restore test on isolated EBS is still **NOT CERTIFIED** |
| Monitor / alarms | No canonical chain/header attestation | `modern/monitor.py` requires independent reference and Heimdall; restore short-circuit previously hid disk use | **FIX IN SOURCE**: PR #6 reports real disk on maintenance and no fabricated 0% metric; installed release has not yet been promoted |
| Archive / history | Pruned 2022 snapshot | Current Bor `gcmode=full`, PBSS `state.scheme=path` | **DO NOT CLAIM ARCHIVE STATE**. Full old block files do not prove historical `eth_call` state; benchmark retention and preserve external archive lane |

## Canonical recovery decision

Restoration evidence at ~2026-11-08T06:31:00Z: pinned base compressed bytes **2,922,810,195,156 complete**, increment **1,827,986,735,104 / 3,844,656,567,849**, guarded worker alive ~86 MB/s, ~3 TiB free of 8 TiB. Heimdall-v2 fresh and `catching_up=false`. Bor inactive and RPC readiness FAIL because the owned maintenance lock is in place. This is **positive restore progress, not native node certification**.

Run the new **read-only, source-only** recovery triage locally after its governed release:

```sh
python3 modern/recovery_advisor.py
python3 -m unittest discover -s modern/tests -p 'test_recovery_advisor.py' -v
python3 -m unittest discover -s modern/tests -p 'test_restore_monitor_telemetry.py' -v
```

The triage cannot stop services, modify files, run a new restore or enable LIVE. When a source snapshot is advancing and maintenance is owner-consistent, it selects **continue existing restore only**; it also reports component replay, new pruned snapshot, new native sync, isolated EBS restore and external RPC as *planning-only alternatives requiring independent authorization*. It never claims private RPC certification from a listening port or from restored byte count.

## Acceptance

Only a new **immutable, approved node source release** installs updated monitoring and recovery-advisor code. The current host may remain pinned to old source until its ongoing extraction, native acceptance and change-control window are complete. `main` merged != host installed != node synchronized != mainnet execution certified.

Native node certification still requires Bor/Heimdall P2P, chain 137, head/hash agreement with independent references, bounded historical state and logs, WSS, cold restart, consumer-path benchmarks and separate isolated-volume backup test. No node host grants signing or broadcasting authority to Asset Hunter, APEX or SYMEN.

## Official technical context

- [Polygon Labs Bor v2.11.0 / Uburu announcement](https://forum.polygon.technology/t/announcement-bor-v2-11-0/22516) (mainnet fork block 96,787,900).
- [Polygon Support snapshot note](https://support.polygon.technology/support/solutions/articles/82000909596-polygon-snapshots) (official Bor archive snapshot support discontinued).
- [Polygon Labs 2026 Erigon deprecation and Bor PBSS archive route](https://forum.polygon.technology/t/sunsetting-erigon-support/21872) (archive mode is distinct and requires deliberate sizing and verification).
