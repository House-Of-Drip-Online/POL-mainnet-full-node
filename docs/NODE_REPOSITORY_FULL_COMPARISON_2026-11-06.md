# OMEGA Polygon 137 — Complete Two-Repository Node Comparison and Single Selection

Date: 2026-11-06. State: **source-audited; neither legacy node deployment is running or production-certified.**

## Exact inspected source versions

| Source | Main SHA reviewed | Legacy components | Role |
|---|---|---|---|
| `House-Of-Drip-Online/POL-mainnet-full-node` | `1c94d4a3036328c34063cf28649edccbe040ab89` | Bor v0.2.5 / Heimdall-v1 v0.2.1-mainnet, Ubuntu 18.04 / Vagrant / Ansible, 2021 snapshots | **SELECTED canonical modernized build owner** |
| `House-Of-Drip-Online/dappnode-polygon` | `c05c82ab99cb82188c6b6be50ff194fb1447c83f` | Bor v0.2.14-tmp-span-hotfix / Heimdall-v1 v0.2.8, Go 1.16 Alpine builds, 2022 snapshots | Historical container reference; not an active OMEGA node |

### Exact reviewed files

POL node: `README.md`, `Vagrantfile`, `run.sh`, `ansible/deploy.yml`, `ansible/bor.yml`, `ansible/heimdall.yml`, `ansible/docker-compose.yml`, `ansible/templates/docker-compose-bor.j2`, `ansible/templates/docker-compose-heimdall.j2`, `ansible/docker-install.yml`, `ansible/download-snapshots.yml`, `ansible/extract.yml`, `ansible/test-insync.yml`, `docs/SOURCE_AUTHORITY_MATRIX.md`. DAppNode: `README.md`, `dappnode_package.json`, `docker-compose.yml`, both component Dockerfiles and entrypoint scripts, `releases.json`, `setup-wizard.yml`, `docs/SOVEREIGN_ADMISSION_ALIGNMENT.md`.

## 20-dimension engineering comparison

| Dimension | POL-mainnet-full-node | dappnode-polygon | Decision basis |
|---|---|---|---|
| Mainnet compatibility today | FAIL: legacy clients, v1 Heimdall | FAIL: legacy clients, v1 Heimdall | Both require complete client upgrade |
| Bor version baseline | v0.2.5 | v0.2.14 temporary hotfix | Neither usable at current fork |
| Heimdall version baseline | v0.2.1-mainnet | v0.2.8 | Neither meets Heimdall-v2 migration |
| Official 2026 hardfork support | Missing | Missing | Restore via v2.11.0/v0.13.2 release lock |
| Infrastructure provisioning | Ansible playbook | DAppNode host assumptions | POL |
| Portability to dedicated EC2 | Good structure, bad old content | Docker yes, DAppNode-specific wiring | POL |
| Container multi-service orchestration | Two Compose templates | One Compose plus service lifecycle | DAppNode pattern |
| Pinned reproducible builds | Legacy git tags; not image digest-pinned | Tags; build from source, no immutable image digest | Both insufficient |
| Bootstrap/snapshot integrity | Optional MD5 checks commented out | Snapshot downloads without independent verified modern manifest | Neither |
| Current snapshot compatibility | 2021 snapshots | 2022 snapshots | Neither; require trusted current v2 snapshot or genesis |
| Heimdall-to-Bor integration | Old REST/AMQP | Old REST/AMQP | Rebuild with current interfaces |
| RPC authorization | Public bind, wildcard CORS/vhosts, `admin`/`debug` | Public bind, wildcard CORS/vhosts/txpool | Both unsafe as shipped |
| RPC WebSocket | Configured | Configured | Both need private-only binds and authenticated gateway |
| Historical event indexing | Not established | Not established; pruned snapshot | Historical provider/index remains necessary |
| Deep archive state/tracing | Not certified | Not certified, explicitly pruned | Separate archive-capable lane |
| In-memory liquidity state cache | Absent | Absent | Must belong to Asset Hunter's market state fabric |
| Automatic chain-head hash attestation | Absent | Absent | Added read-only gate in POL `modern/` |
| Tail latency and overload metrics | Absent | Absent | Must instrument/benchmark |
| Integration with existing AWS ECS | Dedicated host/VPC route natural | Needs adapter for DAppNode lifecycle | POL |
| Existing deployment validation | Unbuilt | Unbuilt | Both: no claims of running instance |

**Selection:** one governed RPC infrastructure source: `House-Of-Drip-Online/POL-mainnet-full-node`, branch `main`. Do not merge the two projects or delete the DAppNode reference. Source modernization does not establish an active, permissioned VPC deployment.

## Official release authority

- Bor v2.11.0: official GitHub release `https://github.com/0xPolygon/bor/releases/tag/v2.11.0`, Uburu activation on Polygon 137 block 96,787,900. Older Bor clients stopped at this fork.
- Heimdall-v2 v0.13.2: `https://github.com/0xPolygon/heimdall-v2/releases/tag/v0.13.2`, Karwar activation at Heimdall mainnet height 57,006,000. The old Heimdall-v1 setup is not usable as a new mainnet node.
- The modern source path locks **all four official AMD64 `.deb` artifact SHA-256 digests** from GitHub release metadata. This is artifact integrity evidence, not certification of a successfully installed node or signature verification.

## Asset Hunter live-bottleneck causal attribution

Source: `/asset-hunter/prod`, Asset Hunter ECS task definition :132, hydration progress at Polygon block **96,835,098**, 768 attempts. These are **per-batch** counts; transport lease deferrals are cumulative/provider/workload and must not be counted as pool failures.

| Observed outcome | Count | Can a modern private RPC fix it? | Required next engineering action |
|---|---:|---|---|
| Verified USD price missing | 571 | **Indirectly**: more native quotes / fresh pinned reads can supply graph edges; no invented USD allowed | Complete native quote evidence acquisition in a separate quote graph pass, resolve up to 8-hop native USD paths to two distinct, venue/pool-disjoint oracle anchors, then re-evaluate each economic asset |
| Protocol identity not proven | 84 | **Indirectly**: reduces selector timeouts but does not identify ABIs or factories | Expand verified factory provenance, fee/state getters, Curve/Balancer/DODO-specific ABI decoding and codehash/family classification |
| Retryable RPC transport | 73 | **Directly**: private concurrency and lower VPC RTT may reduce deferrals | Add private Bor provider to adaptive fabric with measured queue depth, freshness and fallbacks; prove actual throughput |
| Fully priced, below $10k verified TVL | 40 | **No**, unless the original valuation was incomplete/incorrect | Keep excluded when independent full per-asset USD TVL is below the floor; allow complete repricing only when market state changes or previous proof invalidated |

Also seen: **97,050 cumulative hydration lease deferrals** for one public RPC provider, **not distinct affected physical pools**.

### Important source-level graph scheduling limitation

Current Asset Hunter implementation has `CrossInvariantUsdGraph.DEFAULT_CROSS_INVARIANT_POLICY.maxHops = 8`, two native quote paths to distinct oracle anchors, 100 bps agreement threshold, and a $10k anchor-side reserve. However, the actual `LiveSurfaceDiscoveryService.hydratePool()` builds native quotes and then immediately tries the same pool's USD TVL valuation, while **other pools hydrate concurrently**. `UniversalUsdResolver.begin()` resets the quote graph on a new pinned block. This means an eligible 5–8-hop conversion may not yet be populated when valuation occurs, even though its upstream pools are in the census. A private RPC makes reads faster; it does not repair this *order-of-evidence* dependency.

**Follow-on Asset Hunter fix (separate repository authority):** one scan-pinned state/identity pass; a fair native-quote graph-building pass; a bounded, two-disjoint-path USD certificate pass; finally pool TVL, Stage-5, route input publication. Preserve deterministic block/hash identity, staged retry budgets, exclusion of the valued pool from its own price path, and never count unpriced assets as zero. Use actual native adapter math for CPMM, CLMM/Algebra, Curve, Balancer and DODO; never substitute a V2 reserve ratio for other invariants. Record whether proof is unavailable, search budget truncated, stale, disagreed, or truly absent. This is **a required implementation**, not a completed result of the node release package.

### Distinct eight-hop requirements

- **USD valuation:** at most 8 real, block-pinned, native-quote graph edges per independent token-to-USD anchor path. Cross-invariant price path may be evidence, not a realized swap.
- **Arbitrage:** 2–8 atomic executable swaps optimized independently by APEX and SYMEN, bounded flashloan principal at **15% of the minimum verified route-pool TVL**, fully costed (flash fee, pool fees, gas, relay, risk, slippage). SHADOW cannot claim a profitable receipt; only live canonical settlement and independent reconciliation do.

## Expected benefit and how to quantify it

**No production uplift is measured yet.** A correctly provisioned same-VPC local RPC may eliminate *external provider per-query* expenses on calls actually routed to it, reduce internet RTT, reduce public-provider admission deferrals, and permit local trace methods subject to node retention and actual CPU/IOPS capacity. It does **not** guarantee mempool completeness, zero latency, full privacy from P2P peers or cloud infrastructure, unlimited read throughput, or an archive proof on a pruned node.

For a fair A/B SHADOW test, replay the same timestamped, block-pinned pool identity and hydration job mix and compare:
1. RPC admitted/completed/deferred, `429`/timeout rates, p50/p95/p99 latency and latency-by-method;
2. historical `eth_getLogs` completion/coverage, pinned `eth_call`, `eth_getCode`, `eth_getBlockByNumber` hash consistency;
3. state/identity/TVL transition counts; number of new certified distinct USD tokens and 5–8-hop two-path certificates;
4. exact route-input pool count, independent APEX/SYM routing acceptance, and all-cost SHADOW simulation passes;
5. EC2/storage/network/IOPS/logging/snapshot expense **versus** the commercial RPC cost it replaces.

Do not assign a fabricated “X% faster” or “Y more profitable trades” without matched live data. OMEGA should retain at least one independent external provider as failover and corroboration. A standalone full node may not serve old archive state needed for selected block-pinned historical simulations.

## Hardware, security and release boundaries

Plan multi-TB high-IOPS storage, significant CPU/RAM, and private same-region network; Polygon’s operating guidance cites 8+ vCPU/32 GB baseline with higher recommended resources and multi-TB history needs. An EC2 instance and 4–8 TB of AWS storage may cost **well above $400/month**, before snapshots, egress and operational labor. Cost formally before provisioning, prefer incremental stages rather than claiming cheaper than Alchemy unconditionally.

P2P peer ports need controlled exposure for connectivity; restrict HTTP 8545/WS 8546 exclusively to internal consumers through VPC security groups/auth proxy, avoid wildcard CORS and privileged RPC APIs, use IAM/SSM and CloudWatch alarms. Node must not contain strategy signing keys. Keep source authority independent and preserve APEX/SYM engine autonomy.

## Implemented source milestone / unverified milestones

New `modern/` in selected repo contains: official release manifest with four asset SHA-256 values (detached signatures not yet verified), download-only Ansible playbook (never auto-installs/starts services), fail-closed read-only Polygon RPC gate, nine gate tests plus two lock/stager tests, and deployment runbook. Local verification: **11/11 Python tests PASS**, PyYAML parses the playbook. This does **not** prove Ansible execution, package download, full node bootstrap, Ethereum L1 RPC dependency, Heimdall sync, Bor sync, production workload capacity or any arbitrage receipt. Continue in that order after governed resource authorization.