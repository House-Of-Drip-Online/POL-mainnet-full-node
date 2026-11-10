# OMEGA Polygon 137 — non-destructive capacity recovery and live monitor promotion

Date: 2026-11-10 UTC. Node: `omega-polygon-137` in `us-east-1`.
This is an operator evidence record, not an assertion of LIVE trading readiness.

## Source and authority boundaries

- Canonical node source: `House-Of-Drip-Online/POL-mainnet-full-node`.
- Verified monitor source release: `8f12dc81fe01648056051b87adb285e2a6fbd7f2` (PR #10).
- The CloudFormation stack `SourceCommit` remains `d961c2c9b0c28f2e99b1747e4786451e0b485e3f`, representing its infrastructure-source parameter. Do not confuse it with the active monitor settings `sourceCommit`.
- The monitor-only promotion compared the installed tree against the exact GitHub checkout: only `modern/monitor.py` and `modern/tests/test_restore_monitor_telemetry.py` differed. Consensus, gateway, release locks, bootstrap and snapshot code were identical. The 78 Python unit tests passed before promotion.
- The two changed files were installed atomically after a new SHA-pinned source checkout; previous files and settings remain in a local rollback directory. Monitor settings record the matched GitHub commit and archive digest. Bor, Heimdall and the gateway were not restarted.
- CloudWatch proved real `BorPeers`, `HeimdallPeers`, `NodeLagBlocks`, `RPCGateFailed` metrics and a health record with `sourceCommit=8f12dc81...` after promotion.

## Disk expansion: accepted change scope

- Identical existing EBS data volume: `vol-0e42262dbe039257e`.
- CloudFormation stack: `omega-polygon-137`; change set: `omega-node-capacity-16t-20261110`.
- Review gate: *only* `AWS::EC2::Volume DataVolume` was modified, `Replacement=False`, with a single changed property (`Size`). All other resources and stack parameters remained unchanged except `DataGiB: 12288 -> 16384`.
- AWS read-back: `UPDATE_COMPLETE`; data volume `16384` GiB, `gp3`, 16000 IOPS, 1000 MiB/s; original instance and volume retained.
- Verify the mounted device and XFS signature before using `xfs_growfs /data`. The successful online grow changed the filesystem from 3,221,225,460 to 4,294,967,280 4-KiB blocks without formatting or unmounting.
- Observed after grow: about 5.2 TiB free, 67.65% utilization; Bor, Heimdall, RPC and monitor active; RPC comparison 0 blocks behind at the checked instant.
- The additional 4096 GiB incurs ongoing provisioned-storage costs. Using the previously observed rate of $0.08 per GB-month, the incremental estimate is $327.68/month, excluding snapshot growth and other charges; verify bills and current rate rather than presenting this as a guaranteed invoice.

## Retained restore data must not be deleted

- A historical restore workspace under `/data/bor/full-restore/524b87...` occupies approximately 6.1 TB. A separate newer stage under `/data/bor/full-restore/2938c76...` has a completed structural manifest; its `canonicalStateVerified` field is false.
- A sampled historical stage ancient-data file and an active `/data/bor/data/bor/chaindata/ancient/chain` file had **identical device and inode**, with hard-link count 2. The apparent 6.1 TB stage size must **not** be treated as 6.1 TB safely reclaimable; deleting any directory path can affect rollback and inode-link ownership.
- No blanket `rm -rf`, automatic pruning, hard-link unlinking or snapshot-stage promotion is authorized by this document. Recoverability must be demonstrated against a separate restored copy before any cleanup decision.
- The active Bor database, `chaindata.rejected-...`, restored stage, and DLM recovery points have distinct provenance and retention requirements. DLM snapshots are crash-consistent and are not a substitute for a verified application-level recovery drill.

## Gate and lifecycle

1. Verify volume ID, current CloudFormation state, attached device, available XFS space and fresh disk telemetry.
2. Verify Bor and Heimdall remain active; check canonical block hashes and lag against an external reference; require fresh time-stamped health records.
3. Preserve `executionAuthorized=false`; do not enable signing or broadcast.
4. Require a source-matched monitor health event and new metric samples. A CloudWatch alarm that has not yet transitioned to OK remains open even when fresh below-threshold samples are visible.
5. Run the separate 25-cycle native RPC AND route-market-data consumer certification. The previous 25/25 local RPC pass is **not** evidence that Asset Hunter, APEX and SYMEN have completed 25 end-to-end cycles.
6. Before future capacity changes or restore cleanup, demonstrate a durable restore test and review expected EBS capacity, performance limits and cost.

## Evidence storage

- Node health stream: `/omega/polygon-node/omega-polygon-137 / node-health`.
- Previous 25-cycle native local RPC evidence: `rpc25-certification-20261110` in the same CloudWatch log group.
- CloudWatch log retention is configured for 30 days, so certification records should be exported to durable evidence storage before expiration.
- Production readiness and RPC transport must not be conflated with independent consensus proof or economics/execution certification.
