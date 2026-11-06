# OMEGA Polygon 137 Private-Node Modernization — 2026-11-06

**Canonical source owner:** `House-Of-Drip-Online/POL-mainnet-full-node` (`main`).  
**Source status:** Release-staging and RPC-gate logic are locally testable. **No node or AWS EC2 instance is provisioned, installed, synchronized, or performance-certified by this code alone.**  
**Execution authority:** Data infrastructure only; SHADOW-first, not a signer, strategy engine, profit publisher, or broadcasting permission.

## Repository comparison and decision

- `POL-mainnet-full-node`: Ansible-based deployment, previous Bor `v0.2.5`/Heimdall-v1 `v0.2.1-mainnet` and 2021 snapshots. Obsolete and unsafe; old Vagrant Ubuntu 18.04 and open, wildcard HTTP/WS/admin/debug RPC must **not** be used. Chosen for modernized deployment authority because Ansible integrates more cleanly into dedicated AWS EC2 host configuration, release locks, and host security controls.
- `dappnode-polygon`: Docker packaging is more comprehensive, but older Heimdall-v1 `v0.2.8` and Bor `v0.2.14-tmp-span-hotfix`, 2022 snapshots, 2021 Go builder, public RPC bind, and DAppNode-specific host assumptions. Keep as an independent, **non-authoritative reference**; do not merge its obsolete code or run two competing node deployments.

## Release and network hard locks

The version-pinned `release-lock.json` records official 0xPolygon release-asset SHA-256 values for Bor **v2.11.0** and Heimdall-v2 **v0.13.2** on **mainnet 137**, AMD64. These are independently published stable releases compatible with the November 2026 Uburu and Karwar hardforks. Verify latest advisories prior to deployment. Never use original 2021/2022 genesis/snapshot URLs or v1 Heimdall. Heimdall-v2 requires its migrated mainnet genesis and current configuration; never copy v1 configuration verbatim.

## Staging build (no new cloud charges)

With a user-provisioned private Linux AMD64 instance, a configured Ansible controller, and explicit authorization to install to that host:

```sh
ansible-playbook -i your-private-inventory.ini modern/stage-signed-releases.yml --check
ansible-playbook -i your-private-inventory.ini modern/stage-signed-releases.yml
```

The playbook downloads **four SHA-256-verified official `.deb` artifacts** into `/var/cache/omega-polygon-node/releases`. It intentionally does not install binaries or start services; installation, snapshot bootstrap, VPC/firewall configuration and all provider activation remain separate acceptance milestones. **Do not run the obsolete `ansible/deploy.yml` or `Vagrantfile`.** This is a verified package-staging milestone, not an entire deploy.

## RPC acceptance gate

After the modern Bor+Heimdall-v2 nodes are installed and synchronized, evaluate using a truly **independent** Polygon provider:

```sh
python3 modern/rpc_gate.py \
  --local-url http://127.0.0.1:8545 \
  --reference-url https://YOUR_INDEPENDENT_POLYGON_RPC_ENDPOINT \
  --max-lag-blocks 2 --max-head-age-seconds 120
```

Returns JSON `status=PASS` only when both endpoints are chain 137, the local node is not syncing, its head is fresh and within a bounded lag, and both agree on the **same pinned block hash**. Exit status `2` blocks promotion. The JSON omits RPC URLs/keys. Two different endpoint URLs do not prove independent node operators; attest the provider operators separately. **This is a necessary, not sufficient, production readiness test.** Also independently verify `eth_getLogs` historical ranges, pinned `eth_call`, RPC burst throughput, WSS subscriptions, reorg rollback, storage/CPU/IOPS, snapshot recovery, and automatic failover under the actual Asset Hunter workload.

## Required OMEGA integration architecture

```text
Polygon P2P -> [Heimdall-v2 + Bor on dedicated private EC2/host]
                          | bounded internal HTTP/WSS RPC (NO public RPC)
                          v
                ProviderFabric/adaptive scheduler
                  |        |            |
          Asset Hunter   APEX SHADOW    SYMEN SHADOW
          full census    independent    independent
          native quotes  evaluation     evaluation
          8-hop USD      2–8 swap       2–8 swap
                          |
                  independent RPC fallback
```

- Dedicated node should be **same-region/same-VPC** as consumers if possible; network RTT is not literally zero and P2P block propagation is not instantaneous. Do not store signing keys on the node.
- Keep P2P ports appropriately peered, but **private/least-privilege** HTTP/WSS RPC access. Disable `admin`/`personal` over HTTP, avoid unrestricted `debug`/`txpool`, use SSM instead of public SSH and no wildcard CORS/public vhosts; rate-limit even internal clients.
- A pruned node may lack requested old state. Keep **archive/historical-capable RPC or independent evidence-indexing** for factory event-history recovery and deep fork work, plus separate externally operated provider for correctness corroboration and failover.
- Emit per-provider admissions, deferred leases, transport errors, cumulative pool stage recoveries, latency histograms, and verified USD certifications; compare old/new on the **same block-pinned workload** before changing provider weight.
- Do not treat an RPC lease deferral as a distinct failed pool or a verified TVL deficit.

## Measured recovery basis (Asset Hunter :132, Nov 6 2026)

One 768-attempt census batch recorded 571 unresolved USD valuations, 84 protocol identity failures, 73 retryable transport failures, and 40 fully priced below-$10,000-TVL pools. PublicNode hydration admissions also showed **97,050 cumulative deferrals** (not 97,050 distinct pools). Private-node capacity directly targets the transport/admission bucket; identity repair and cross-invariant USD two-path proof are separate requirements. The `CrossInvariantUsdGraph` supports eight quote hops, but it only sees valid native quotes already hydrated **at the same snapshot** and does not guarantee that a graph path exists or that it is independent. Never lower the $10,000 pool admission floor or fabricate an unpriced token's USD value.

## Deployment gates left open

1. Owner-authorized, costed AWS host and non-root identity (or pre-existing host), private network + disk budget.
2. Official package installation plus matching mainnet genesis/snapshot and Bor/Heimdall synchronization.
3. RPC gate PASS and independently operated provider corroboration.
4. Historical log completeness and exact-block `eth_call` functionality under workload.
5. Differential benchmark: timeouts, p50/p95/p99 latencies, deferrals, qualified pools, cross-invariant certificates, resource and provider costs.
6. SHADOW-only integration: Asset Hunter first, APEX+SYM independent consumer validation, no signing/broadcast.

For a contemporary Polygon full node, budget **multi-terabyte SSD/NVMe and substantial compute**. Actual AWS pricing and storage requirements must be costed against live region/instance/storage quotes; do not rely on a generic $150–$400 monthly node claim.