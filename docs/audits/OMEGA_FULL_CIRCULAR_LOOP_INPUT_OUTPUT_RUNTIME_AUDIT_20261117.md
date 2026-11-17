# OMEGA — Polygon → Asset Hunter → APEX / SYMEN → GTTM
## Complete circular-loop input/output contract and measured production checkpoint
**Date:** November 17, 2026 · **Chain:** Polygon 137 · **Result:** INCOMPLETE / SHADOW CERTIFICATION HOLD  
**Scope:** Read-only AWS SSM, ECS, CloudWatch and current `main` source. Existing route canon, OMEGA-ABA-PRICE-001, UFSBCA, GTTM and independent strategy authority remain governing. This document is operational evidence, not new trading authority or a claim that a deployed program has been repaired.

### N. Polygon node: repeated real execution-state loop
N0 boot: EC2/mounts, Bor, Heimdall, timer and gateway → instance/process/volume identity, service errors and uptime.
N1 consensus/peers: Heimdall sync, height/hash/time/peer count → independent Heimdall readiness.
N2 Bor import: canonical block number/hash/time, verified receipts/logs/state, peer count, CPU/IO and lag → raw native state (NOT executable until gate passes).
N3 gate: compare independent Polygon chainId 137, `eth_syncing`, max head age, lag, and pinned canonical hash → `/run/omega-polygon/readiness.json` with PASS/FAIL, typed reasons, timestamps, observed lag and `executionAuthorized:false`.
N4 HTTP on private host :8545, upstream 127.0.0.1:18545 → bounded permitted JSON-RPC methods, latency, failure/rate metrics; 503 NODE_NOT_READY on failed gate.
N5 WSS private :8546 → only permitted newHeads/log subscriptions, handshake, reconnect, source head parity; refuses when gate fails.
N6 monitor timer → periodic gate revalidation (the oneshot `omega-monitor.service` can be inactive between successfully scheduled checks); state repeats as block head changes.
**Observed:** EC2 `omega-polygon-137` m7i.4xlarge running, Bor and Heimdall running, gate timer active, Bor imported lagging blocks, Heimdall catchingUp false with 135 peers, Bor 100 peers. Readiness gate FAIL: LOCAL_HEAD_STALE, LOCAL_SYNC_INCOMPLETE, NODE_LAG_LIMIT_EXCEEDED; measured lag 12404 then 12342 blocks. Gateway HTTP/WSS 503 NODE_NOT_READY. Genuine 25-sample native localhost RPC diagnostic: 25/25 successful `eth_blockNumber` replies, 0/25 gate PASS, block 97486050 → 97486159 (+109), median latency 1.0ms, min 0.8, max 21.5. These are NOT 25 certified OMEGA strategy cycles. Bor internal upstream is reachable; preserving fail-closed gateway is mandatory.

### H. Asset Hunter: native-census and external-advisory dual loops
H0 boot/lease: environment, identity, provider-fabric, EFS persistent census, RDS registry, exclusive producer lease → worker lease proof/health.
H1 native provider observation → >=1 healthy chain137 native RPC capable of the required method and block consistency; successful probe counts, error/latency/quarantine.
H2 canonical snapshot → block number/hash, source providers and observation time; no native authority if H1 unavailable.
H3 independent external advisory intake → provider/market observations, pool candidate queue, corroboration and contradictions; NEVER execution-authoritative without H1/H2.
H4 high-priority HOT native refresh → selected physical pool IDs, exact state/reserves/ticks, verified TVL, native quote/call capability, per-pool typed rejection and backpressure budget.
H5 pool DNA/registry → contract/physical pool ID, token addresses/decimals, prices per token with reference/quote distinction, protocol family, fees, liquidity, USD confidence, exact block/hash and provenance.
H6 verified graph and publication → nonempty signed immutable generation with source block/hash, authenticated registry version and physical edges; zero arbitrary 100/5000-pool gate; do not relabel stale cached state as fresh.
H7 independent consumer handoff → APEX and SYMEN each verify signature/identity and separately acknowledge exact registry version; producer-side readiness assessment is NOT consumer ACK.
H8 background 20-phase persistent census → full pool universe, native enumeration, external reconciliation, roots/factories, token metadata, $ valuation, qualification queue; durable cursor, attempted/evaluated/RPC-deferred/evidence-deferred counts.
H9 checkpoint and feedback → persist EFS/RDS evidence, move retry queues, use GTTM stage spans, schedule next HOT cycle independent of full census.
**Observed:** `asset-hunter-prod:195` running healthy container; rotation false and no individually named fallback RPC secret bindings in inspected ECS container. Current active worker cycles fail at `provider_observations` with `PROVIDER_AVAILABILITY_LOST` while external advisory intake persists. API /healthz 200 is NOT native readiness. Native signed registry returned version `0xa6e9b2a19f5dc3968f75dcad126c0f988849962cd033e7a20a03ab0ee9f45a34`, 84 surfaces, age ~71634 sec at readback (NOT fresh). Latest census 218117, pass3 evaluated 28389, notYetEvaluated 189728, neverAttemptedThisPass 158790, deferredRpc 16190, deferredEvidence 14748, policyExcluded 0, completedPasses 2, censusComplete false. Signed graph V2 40, V3 32, Algebra 12; 59 fully USD-valued, 84 quote-capable but stale.

### A. APEX-OMEGA: independent C1, receipt-bound C2, liquidation and financing loops
A0 startup: SHA/digest, SHADOW flags, RPC/WSS health, contracts, Rust authority and GTTM → exact environment readback and readiness reasons.
A1 ingest authenticated Hunter graph + source digest/block/hash → independent consumer ACK, accepted surfaces, rejected lineage, active-graph identity.
A2 native snapshot hydration + topology → verified execution graph, physical uniqueness and token continuity; structural census edges remain research-only.
A3 independent graph search → 2–8-hop A–B–A closed candidates by root with complete/pruned/deferred search accounting; C1, LQ and C2 authorities never conflated.
A4 exact route quotes/call proof → per-hop amounts, protocol native fees, decimals, direction (two-swap BUY<SELL), invariant block/hash and calldata.
A5 lender and X sizing → Balancer/Aave feasible principal, exact 15% route-wide minimum verified TVL, lender premium/size and actual route depth.
A6 Rust-authorized economics → complete gross/net after gas/flash/relay/risk, strict >0 and >=$5; type-coded rejected/accepted evidence; no synthetic profits.
A7 global net ranking + Top50 successful builds → source/digest, rank, X*, complete payload hash, failures consume zero slots.
A8 Green original SIMULATION_PENDING → immutable clone to Anvil, minOut/repayment/gas/net and receipt proof → PASS promotes original; FAIL/INDETERMINATE holds/rejects within bounded policy.
A9 Purple → fresh-state, nonce, deadline, reprice, payload hash, signer authority → SHADOW would-transmit only (LIVE signing disabled).
A10 C1 settlement evidence (only genuine successful receipt, not SHADOW fiction) → state reload → C2 recomputes fresh post-C1 same-surface prices within 2 blocks /5 sec, exactly one MIRROR/REVERSE/NO_OP per receipt. Reverted C1 → NO_OP.
A11 LQ independently observes lending market and builds liquidation candidates via own policy/capital/simulation; funding/basis separate lane; emit typed decisions.
A12 telemetry/reconciliation and next snapshot → graph generation/route counts, successful build, fork receipt hashes, precise GTTM times, rejection waterfall, SHADOW decision; no realized settlement without actual LIVE on-chain receipt.
**Observed:** `apex-omega-shadow:204` ECS running/healthy; LIVE_ARMED false, LIVE_TRADING false, OMEGA_LIVE_BROADCAST_ENABLED false, OMEGA_MODE shadow, MAX_ROUTE_HOPS 8. `OMEGA_DISCOVERY_MIN_PHYSICAL_POOLS_FOR_SHADOW=100` configured, contrary to no-minimum policy; actual enforcement must be code-proven. APEX accepted stale 84-surface graph, native graph conversion repeatedly results in `NO_TVL_QUALIFIED_POOLS`, `WAITING_FOR_DISCOVERY`, and WS transport failures. No positive-net fork trace demonstrated. Distinct `apex-omega-governed-graph-ingress:16` uses `OMEGA_GRAPH_INGRESS_MAINTENANCE=true` as a dedicated write-authorized ingress role by source design; do not assume the mere flag equals a shutdown.

### S. SYMEN: independent full strategy loop
S0 source admission/startup → signed Hunter version, source body hash, correct exact tokens and readiness; SHADOW only.
S1 scan/market coverage → scan_id, block, token registry, source coverage and independent graph ACK.
S2 graph/routes → directed physical edges, 2–8 closed cycles, route count and complete/pruned/deferred limits.
S3 lenders and requested principal → feasible provider/sizes, 15% verified TVL cap, sampled/deferred accounting.
S4 native exact quote and GTTM → per-hop in/out amounts, actual BUY/SELL directional evidence, same-block hash, flash fee, quote latency and typed failure.
S5 pre-gas rejection → negative gross after flash fee classified explicitly, never represented as full-cost net.
S6 gas and full economics → native execution gas probe, oracle USD conversion, complete charges and expected net; >=$5 threshold; no uncosted acceptance.
S7 sampled X optimization + ranking → best *sampled* principal/provider, `global_optimum_certified:false` when bounded; deterministic route ranking, shortlist/slot evidence.
S8 risk/capital/authorization + fresh state → risk, capital reservation, OMEGA-ABA-PRICE-001, GTTM deadline, exact execution package.
S9 simulation / paper outcome → exact payload fork proof or typed reject; SHADOW no actual network submission, paper reconciliation separately labeled.
S10 feedback + persistent cycle summary → evidence hash tip, scan/cycle identity, quoted/economic/authorized/sim-pass/rejected/failed counts, best net, p50/latency stage metrics; repeat.
**Observed:** `symen-prod:105` task healthy but rollout IN_PROGRESS at ECS inspection, API `/v1/runtime/run` state `IDLE`, completed cycles=0 for current runtime. `/v1/runtime/last-cycle` shows older historical `cycle_2f843c721dd33638de867b27` completed 2026-11-17T01:00Z, 24 quotes, 0 authorized, 0 simulation passed, with different registry version `0x829d73c18e2f6c6080a910159148317b9604619521077ccf77edee8c03009dac`. Old cards with price evidence do not prove a new healthy cycle.

### G. Global GTTM / OMEGA COMMAND
G0 zero-origin system odometer, independent Trip A/Trip B, monotonic local spans and cross-host offset-aware time.
G1 stage event schema: system/lane, immutable scan/cycle/route/pool id, source block/hash, task start/end, stage duration, outcome/rejection, durable cursor.
G2 aggregate p50/p95/p99 discovery, RPC, quote, Rust economics, build, Anvil, Purple; include queue vs CPU vs I/O; missed deadlines, discarded work and retry reasons.
G3 economic funnel: 218117 census → HOT verified → signed generation → consumer ACK → executable edges → constructed routes → quotes → capital-size candidates → positive net → Top50 build → Green sim → Purple SHADOW.
G4 operator/audit: effective config, provider status, source SHA, ECR digest, ECS revision and graph identity. Unknown fields shown UNAVAILABLE, never zero.
G5 release: 25 **genuine and consecutive** per-engine SHADOW cycles with every requisite stage and no mock native data, exact source/deployed parity, separate CV certification; no LIVE command authority implied.
**Observed:** stage-specific logs and timing functions exist. Full global COMMAND integration and genuine 25-cycle strategy proof remain UNVERIFIED.

### Current hard-blocking dependency and safe sequencing
1. Node must achieve canonical chain 137 head/hash parity; preserve the strict 503 gateway while Bor catches up. Do not fake ready state. Verify an end-to-end 25-cycle pass after node readiness recovers.
2. Repair provider source bindings and fallback at ECS/IaC runtime (private primary preferred; at least one native healthy provider suffices). Never use external advisory quotations as canonical reserve-state substitute.
3. Restore fresh Hunter HOT registry and keep both native census and independent external advisory running. Verify every active surface DNA, exact provenance and two separate signed consumer ACKs.
4. Remove active global 100-pool readiness threshold in APEX through tested source and immutable deployment; verify zero-threshold entry with 1+ valid graph route.
5. Restore native executable-edge hydration and exact-size price direction, capital/complete net, and Top50.
6. Independently certify Green→Anvil→Purple SHADOW traces for APEX and SYMEN, C2 post-C1 receipt semantics, and GTTM.
7. Reconcile all four current main SHAs with tested immutable ECS/image/EC2 source; no runtime behavior is established by documentation alone.

**Decision:** Node gate FAIL; Hunter HOT publication FAIL; APEX fresh economic cycle FAIL; SYMEN current-cycle admission PENDING; global SHADOW integration HOLD. The live 25-sample native head diagnostic passed transport but 0/25 readiness, not certification. No LIVE changes or blockchain transaction performed.
