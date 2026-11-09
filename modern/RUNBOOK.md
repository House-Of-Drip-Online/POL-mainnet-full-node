# Polygon 137 operation

## Build and launch

Use `modern/`, not the historical `ansible/deploy.yml` or `run.sh`. Runtime uses
official packages under systemd; the optional Ansible wrapper calls the same
bootstrap. This removes dependence on the obsolete Docker client versions.

```sh
python3 -m venv .venv
.venv/bin/pip install -r modern/requirements-dev.txt
.venv/bin/python -m unittest discover -s modern/tests -v
.venv/bin/cfn-lint modern/aws/node.yaml
.venv/bin/ansible-playbook --syntax-check -i 'polygon_node,' modern/deploy-host.yml
.venv/bin/python modern/deploy.py
.venv/bin/python modern/deploy.py --prepare
.venv/bin/python modern/deploy.py --execute
```

`--owner-authorized-root` is required only when using the owner's explicitly
approved root exception. Account, subnet, image, immutable commit and
non-destructive change-set checks still apply. Inspect the live price and
quota before a subsequent release. The observed base is about $1,353/month
at 730 hours, excluding snapshots, transfer, monitoring and tax. EBS snapshots
bill for stored data and changes, not simply the provisioned 8 TiB capacity.

The instance has a public P2P address to avoid routing bulk chain downloads
through NAT. Only ports 30303 TCP/UDP and 26656 TCP are internet-facing.
Port 8545 accepts HTTP and WebSocket from the explicit client security group.
Bor HTTP 18545, WSS 18546, privileged namespaces, Heimdall REST, and monitoring
ports are loopback-only. No client security group is attached automatically to
existing engines. That attachment is a separate acceptance-driven integration.

## Snapshot bootstrap

Heimdall seed servers supply peer addresses and disconnect. Do not duplicate
their IDs in `persistent_peers`; persistent connections are for full peers.
The bootstrap removes only seed/persistent overlaps, preserving distinct
configured full peers. Peer exchange stays enabled, and its address book is
stored at `/data/heimdall/data/addrbook.json`, writable by the Heimdall service.
The packaged configuration directory can remain root-owned. After a peer
configuration change, restart Heimdall and verify both peer count and advancing
block height; a successful TCP connection alone is insufficient.

An unsynchronized Heimdall is a skipped Bor start condition, not a Bor crash.
The monitor retries admission; the database process must not enter a restart
loop merely because its upstream state is stale. `catching_up=false` alone is
insufficient: the head must also be recent and belong to `heimdallv2-137`.

Independent HTTP checks identify themselves as `OMEGA-PolygonNode/1.0`.
PublicNode was observed to return HTTP 403 for Python's default client identity;
the explicit operator identity returned valid RPC responses. Failed reference
reads still close the gate; changing headers never substitutes for chain, head,
freshness, and pinned-hash verification.

For an application-hash mismatch, retain the failed height and expected/received
hashes. Stop Heimdall and Bor, take a complete consistent database backup, then
use the installed upstream `heimdalld rollback --home /var/lib/heimdall
--chain=mainnet` only after reviewing the failed transition. This replays one
block and is not an automatic health repair. Preserve the node's existing keys
and validator state. Verify progress past the failed height and canonical head
agreement before restoring consumer admission. If replay does not fix the hash,
keep the endpoint closed and investigate or restore verified state; never edit
an expected hash or disable consensus validation.

The first installation downloads recent PublicNode pruned databases with fixed
object size and ETag, records local SHA256 digests, and extracts only database
files as the unprivileged client user. ETag is transport identity, not a signed
state proof. The readiness gate must independently corroborate the live chain.
If a provider replaces an object, the installer stops; inspect and update the
lock through a new source revision rather than disabling the identity check.
Interrupted downloads resume. Existing chain databases are never overwritten.

## Observe

The November 7 compact Bor snapshot is rejected for native full-node use.
`omega-bor-full-restore.service` restores the pinned base plus increment under
`/data/bor/full-restore/`. During restoration, maintenance prevents Bor starts,
but the monitor continues publishing Heimdall head/peer status and transfer
progress. Inspect `progress.json` and the restore journal; bytes received are
not synchronized blocks. Each component has a transport SHA256 completion record.
Completed components survive retries. An interrupted compressed component must
be replayed from its beginning; completed extracted members are compared bytewise.
Conflicting base/increment files stop promotion rather than overwrite each other.

Promotion renames the rejected database to `chaindata.rejected-<timestamp>` and
moves the complete new database into place. Only the restore's own maintenance
reason is cleared. Bor then starts under the existing Heimdall gate, and the RPC
gateway stays closed until native synchronization and independent checks pass.
No pruning offsets, consensus roots or validation rules are changed.

### Expired increment recovery (2026-11-09)

The increment ending at 96,869,437 is no longer available (HTTP 404).
The November 8 worker stopped while extracting receipts segment 1096;
the completed base and incomplete increment remain evidence, not a valid node.
The refreshed lock ends at 96,984,637 and preserves the identical base identity.
Never splice an incomplete receipt segment into a newer snapshot or clear the
maintenance gate to force this database online.

For this recovery, retain the old stage and create a separate stage keyed by the
new lock. The completed base can be reused by same-filesystem hard links after
checking its completion identity, file inventory and total bytes. These shared
immutable base segments are not an independent backup. Do not hard-link mutable
increment metadata. Replay the entire newly pinned increment and retain its
complete stream hash; only the existing structural and native acceptance gates
may promote it.

Preserving the 6.69 TB failed stage while extracting the new increment requires
additional capacity. The prepared storage-only CloudFormation change sets
`DataGiB=12288`, preserves all other parameters, and must show only the existing
EBS data volume changing without replacement before execution. At the observed
us-east-1 gp3 storage rate of $0.08/GB-month, the 4096 GiB increase adds $327.68
per month while provisioned, excluding snapshot growth and tax. Confirm the
volume identity, grow the existing XFS filesystem, then rerun the actual free
capacity check before starting the worker. Do not format the volume.

The restore now writes terminal `FAILED` evidence when a streaming component
fails. Monitoring surfaces `RESTORE_FAILED` and leaves the RPC gate closed.
Failure codes exclude signed transport URLs. A transfer percentage is never
Bor synchronization progress.

The read-only `modern/tools/bor-db-audit/main.go` can be built inside official Bor
commit `3a018e38467594508ca31ebeaf804837fb92834a` with Go 1.26.10. It opens Pebble
read-only and reports state/root metadata and retained-header continuity. Stop
Bor before auditing. The tool is diagnostic evidence, not a full state verifier.

```sh
systemctl status omega-bor-full-restore
journalctl -u omega-bor-full-restore --since '-10 min' --no-pager
cat /data/bor/full-restore/progress.json
```

Use SSM Session Manager; do not open SSH.

```sh
systemctl status omega-bootstrap heimdalld bor omega-rpc omega-monitor.timer
journalctl -u omega-bootstrap -u heimdalld -u bor --since '-10 min' --no-pager
cat /data/bootstrap-complete.json
cat /run/omega-polygon/readiness.json
df -h /data
curl -fsS http://127.0.0.1:26657/status
```

A read-only, source-only six-path triage helper is available at `modern/recovery_advisor.py` after the associated immutable node release is installed. It selects continued guarded restoration while fresh progress and capacity are proven; it never executes a competing restore or grants LIVE authority. Its unprivileged view may use a *fresh* copy of the protected restore record in the existing monitor readiness snapshot, never a stale copy. See [DAppNode reuse/gap closure](docs/POLYGON_NODE_DAPPNODE_GAP_CLOSURE_20261108.md).

The gateway returns 503 while syncing or when corroboration fails. Health
evidence goes to the stack's CloudWatch log group and `OMEGA/PolygonNode`.
Expected initial readiness alarms are not permission to disable the gate.

## Acceptance

After readiness passes, use the private address to verify `eth_chainId`,
`eth_call` at the same canonical block through local and independent RPC,
bounded historical `eth_getLogs` for known factory events, and WSS `newHeads`.
Compare the same workload before changing provider weights. Verify the earliest
available block/log/state ranges and retain the existing providers for gaps.

Restart Heimdall and Bor and observe readiness disappear, WSS reconnect, fresh
heads resume and the independent comparison pass. Test backup restore onto a
separate volume before calling recovery certified. Daily snapshots are
crash-consistent and do not themselves prove application-consistent recovery.

## Recovery

The node and its data volume have retention policies and termination protection.
Do not bypass the bootstrap's refusal to reformat an existing signature. Attach
a restored snapshot volume to a separate recovery host, verify its identity and
XFS label, and test without production consumer access. Avoid concurrent writers
to the same database. Snapshot retention deletes only the tagged snapshots from
this stack after the configured retention count is exceeded.

Increase the data volume before the 80% alarm becomes disk pressure. The gateway
fails closed at 95% used or under 100 GiB free. A later EBS size increase requires
an explicit `xfs_growfs /data` after the block device expansion. No automatic
pruning or data deletion is performed by this release.

## Release upgrades

An initial installation marker binds the client packages to their release lock.
Changing that lock requires a reviewed upgrade procedure; the initial bootstrap
refuses silent upgrades. Keep the prior source, package locks, and recovery
snapshot. Never start an older binary against a newer database without upstream
compatibility evidence. Node readiness does not authorize trading or signing.
