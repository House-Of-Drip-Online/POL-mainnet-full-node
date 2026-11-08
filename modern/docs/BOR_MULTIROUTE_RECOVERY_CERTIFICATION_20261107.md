# OMEGA Polygon 137 — Multi-Route Bor Recovery and Certification Gate

**Evidence observation:** 2026-11-08 01:35–01:38 UTC. This is an operational checkpoint, not a declaration that the node is synchronized.

## Fixed node identity and authority

- EC2 `i-0e9c908e9994086e8`, us-east-1a, `m7i.4xlarge`.
- Bor installed `v2.11.0` (upstream source git `3a018e38467594508ca31ebeaf804837fb92834a`). This is the Polygon 2026-11-05 Uburu-mainnet-compatible release; do not downgrade.
- Heimdall-v2 installed `v0.13.2`; `heimdalld` active, `heimdallv2-137`, CometBFT `catching_up=false`, independently observed advancing blocks (~57,364,584 at checkpoint).
- `bor.service` inactive and disabled **intentionally** while `omega-bor-full-restore.service` owns `BOR_FULL_RESTORE_PENDING`. No bypass of `ExecCondition=monitor.py --bor-start-allowed`.
- The private HTTP/WSS proxy on `10.77.1.77:8545` is **not an operational Bor RPC until native readiness passes**. It fails closed with 503; privileged Bor HTTP is loopback on 18545.
- Instance disk: 8192-GiB gp3 on /data, 16,000 provisioned IOPS, 1000 MB/s EBS throughput. Live `df` 8.0 TiB capacity, ~3.6 TiB used, ~4.5 TiB free. EBS backing is provisioned capacity, not guaranteed chain-data completeness.
- Source root path: `/opt/omega-polygon/modern`; data is `/var/lib/bor` symlink to `/data/bor`; Bor datadir `/var/lib/bor/data`.

## Current guarded restore: **continue / do not interrupt**

The pinned `modern/full-snapshot-lock.json` defines two components:

| Component | Byte-exact compressed size | Max extracted size | Block coverage | State |
| --- | ---: | ---: | --- | --- |
| PublicNode base | 2,922,810,195,156 | 3,150,000,000,000 | 0–75,817,088 | Complete, archived component marker |
| PublicNode increment | 3,844,656,567,849 | 4,300,000,000,000 | 75,817,089–96,869,437 | RESTORING: 303,046,852,608 bytes consumed at checkpoint |

The restore uses verified HTTP 206 range responses, ETag If-Match and byte totals, bounded eight-worker downloads, LZ4 extraction, SHA-256 on the actual compressed stream, no archive path traversal or symlinks, and component-level checkpoints. The ETag is **transport identity**, not chain consensus verification. Component archives are extracted under `/data/bor/full-restore/<lock-digest>`, not into the active Bor database. Never start Bor against an incomplete source.

At completion `full_snapshot.py` must write `restored.json`, merge without overwriting mismatched duplicate files, promote `combined` by same-filesystem rename with the rejected database preserved, clear only the owned maintenance reason and let the normal monitor admit Bor. The node must still prove canonical execution state after boot. Automatic promotion depends on the incumbent authenticated service and permissions; no claim that it has passed.

### Storage safety calculation

Bounded extracted components total 7,450,000,000,000 bytes (6.776 TiB), plus retained rejected chaindata (~107 GiB), margin, journal and OS/EBS overhead. The nominal 8-TiB disk has finite headroom, but check disk use continuously because increments can contain changed files and simultaneous staging can temporarily duplicate paths. Do not run **another extraction or full sync concurrently** on this volume. Raise an alert if free bytes approach required residual expansion plus the required 200-GiB safety margin. Before adding any extra snapshot staging, calculate worst-case transient copies, not just final database size.

## Recovery decision tree — multiple supported routes, one active writer

### Path A: Finish the pinned base+increment (current first choice)

Prerequisites: progress bytes advance, component identity matches, extraction stays within bounds, free disk remains above margin, no error. Continue without interruption. On completion, verify the promoted ancient subdirectory under the **configured** `datadir`, and native Bor header/state metadata. An older rejected chaindata generated `ancient chain segments already extracted, please set --datadir.ancient to the correct path`; this is **not yet proof** that the newly restored database has the same defect. Do not edit `ancient` metadata or blindly set the flag before verifying layout.

### Path B: Resume/replay the affected component safely

Trigger: transport interruption, ETag change, checksum mismatch, archive layout failure, or service exit. Preserve `complete.json` for a verified component. Identify the exact failed component and object; verify snapshot publication and source identity. The current design safely replays an incomplete compressed component from its beginning while byte-comparing already-extracted files. New object identities require a reviewed source lock update and new provenance. Do **not** relabel progress as complete.

### Path C: Pruned current-mainnet Bor snapshot (alternative operational node)

If full-history recovery is economically or operationally infeasible, evaluate a current independently verified pruned/full-state snapshot **on a separate volume or host**. Validate it has the RPC history capabilities OMEGA actually requires. Polygon Support states that Bor archive snapshots are no longer supported due to data growth. A pruned node cannot be certified as an archive; missing older `eth_getLogs`/historical state must route to an archival provider. Any switch requires a separate operator decision, not silent reduction in OMEGA coverage. Ref: https://support.polygon.technology/support/solutions/articles/82000909596-polygon-snapshots

### Path D: Native P2P state sync

Use official Bor v2.11.0 with current Heimdall-v2 on a fresh, empty, appropriately sized data directory. Verify network ID, peers, DNS discovery, checkpoint/finality, CLI version, genesis and strict permission boundaries. Do not combine a new P2P database with the in-progress frozen archive or reuse the old Pebble/ancient data. Estimate sync feasibility from measured block and state catchup, not a guess. Keep canonical validation and public RPC fallback while syncing.

### Path E: Isolated EBS clone / restore

Take a volume snapshot of a **consistent stopped source** or use retained backup snapshots; restore into a **new volume/host** to run independent ancient-layout and startup checks. No concurrent writing to the original Pebble database. Preserve rejected database until a new candidate proves chain/state consistency. Check ownership, XFS mount identity and physical free capacity. Plan cost of duplicate 8-TiB volumes and snapshots before creating.

### Path F: API/RPC continuity while native Bor is offline

Keep existing bounded fallback RPC fabric to live Polygon chain 137 (source-quorum and block-hash corroboration) for read-only discovery and SHADOW. Label it `EXTERNAL_RPC_FALLBACK`, **not** `PRIVATE_FULL_NODE_READY`. Maintain pinned-block calls, freshness, provider capability discovery, rate limits, circuit breakers and no mixing of incompatible snapshots. Do not expose the private gateway or mark it healthy while Bor is offline.

## Completion / certification gates (all required for native node PASS)

1. `progress.json.status` moved out of `RESTORING`; both transport components finished, byte lengths and digest evidence recorded, full source lock matched.
2. `restored.json` generated, original rejected database retained, target contains `CURRENT` and genuine expected ancient chain data; no overlapping-byte conflict.
3. Bor v2.11.0 runs without restart loop; `eth_chainId=137`, net peer connectivity, `eth_syncing=false` for sustained observations and canonical heads advancing near independent peers.
4. Heimdall-v2 network `heimdallv2-137`, `catching_up=false`, advancing consensus height and reachable local Bor→Heimdall endpoint.
5. Local HTTP and WSS privately accessible to an authorized VPC consumer; consistent pinned block hash across independent RPCs; historical `eth_getLogs` and `eth_call` checked **within actual supported retention**; explicit capability inventory for older ranges.
6. Failure/restart recovery proof: Bor and Heimdall restart (only after restore/validation), gate closes during restart and reopens after independent validation, no stale success cached.
7. Actual APEX and SYMEN clients use the intended private node only after `readiness=PASS`; their effective RPC weights and fallback behavior measured and logged. Do not infer wiring from security group membership alone.
8. Provider provenance, current block, source SHA, package versions, task/instance identity and negative-test evidence included in a dated proof package. Node readiness **never** grants LIVE trading authority.

## Actions explicitly forbidden during current active extraction

- Stop or restart `omega-bor-full-restore.service`, kill its LZ4/range reader, erase or rename component directories.
- Change `--datadir.ancient`, modify Pebble metadata, set chain state manually, start Bor while maintenance-owned.
- Trigger multiple competing full-archive restore paths on the same volume.
- Mark the RPC proxy ready merely because it listens on port 8545.
- Use AWS root credentials for new production/IAM mutations; establish least-privilege deployment identity before controlled promotion actions.

## Current operational classification

**RESTORING, not FULL_NODE_READY, not CERTIFIED.** The installed Bor version and advancing Heimdall are independently observed positives. Complete restore and native-state proofs remain blockers. One recovery path is running, while alternatives B–F are evaluated options, not parallel destructive instructions.
