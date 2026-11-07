# OMEGA Polygon 137 node

This is the canonical implementation from `House-Of-Drip-Online/POL-mainnet-full-node`.
It deploys a non-validator data node using official, SHA256-pinned Bor 2.11.0 and
Heimdall-v2 0.13.2 packages and the verified migrated mainnet genesis.

Read [RUNBOOK.md](RUNBOOK.md) for deployment and operations and
[TARGET.md](TARGET.md) for the completion boundary. Deployment is authorized;
the owner's explicit root exception is supported by `--owner-authorized-root`.
The default deployment path still requires a non-root administrative identity.

## Runtime

- Dedicated Ubuntu 24.04 EC2 host, 16 vCPUs and 64 GiB RAM by default.
- Encrypted 8 TiB gp3 data volume, 16,000 IOPS and 1,000 MiB/s provisioned
  throughput. Instance EBS baseline can be lower; measure actual performance.
- Public P2P only; private read RPC on 8545, HTTP and WebSocket on the same port.
- Loopback Bor on 18545/18546, Heimdall REST on 1317 and CometBFT on 26657.
- SSM, IMDSv2, dedicated instance role, bounded logs, disk/readiness alarms,
  daily crash-consistent snapshots retaining two recovery points.
- Heimdall must catch up before Bor starts. Both chains, peers, disk and an
  independent canonical-header comparison govern RPC readiness continuously.
- No signing keys, broadcast APIs, strategy logic, or trading authorization.

## Bootstrap integrity

`release-lock.json` and `genesis-lock.json` contain SHA256-pinned official files.
`snapshot-lock.json` identifies recent PublicNode **pruned** database snapshots
by observed size and ETag. Multipart ETags are not cryptographic signatures.
The installer records a local SHA256, extracts only database files as the client
user, refuses paths/links/devices outside the allowed database root, and never
imports identity keys. Existing databases cannot be overwritten by bootstrap.
Snapshot data is unverified until independent live-chain checks pass.

The selected Bor snapshot has approximately 104 GB compressed state. Its URL's
height and landing-page size differ slightly from object metadata; the lock uses
actual response metadata and refuses any different object. This is a pruned full
node, **not an archive node or a complete historical event index**. Keep historical
providers for Asset Hunter census backfills and unavailable old state.

## Validation

```sh
python3 -m venv .venv
.venv/bin/pip install -r modern/requirements-dev.txt
.venv/bin/python -m unittest discover -s modern/tests -v
.venv/bin/cfn-lint modern/aws/node.yaml
.venv/bin/ansible-playbook --syntax-check -i 'polygon_node,' modern/deploy-host.yml
```

Tests cover canonical-header rejection, fail-closed HTTP/WSS, bounded batches,
broadcast denial, storage/configuration invariants and safe snapshot extraction.
CI is source validation only. Native binary smoke returned chain 137 with the
production-derived Bor configuration; it did not synchronize mainnet. The full
Heimdall genesis verification exceeded the workspace limit and remains a host
acceptance check.

## Consumer admission

Attach the explicit RPC client security group only after readiness and actual
consumer-path checks pass. Preserve external-provider fallback. Benchmark
Asset Hunter's pinned-block hydration workload before changing provider weights;
APEX and SYMEN retain independent execution authority. Transport improvement does
not itself fix protocol identity, quote mathematics or USD valuation defects.
