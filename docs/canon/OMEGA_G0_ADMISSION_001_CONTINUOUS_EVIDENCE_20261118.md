# OMEGA-G0-ADMISSION-001 — Continuous Evidence-Based RPC Admission

Status: APPROVED ENGINEERING TARGET; NOT A RUNTIME CERTIFICATION. Chain: Polygon PoS 137. Authority: SHADOW ONLY.

## Governing decision

1. NO mandatory consecutive-observation count (including 25) SHALL block any RPC request, provider selection, pool refresh, route evaluation, or SHADOW cycle. An optional 25-observation witness MAY be used for commissioning, regression and recovery diagnostics only; it neither controls operational admission nor establishes statistical 99.9% availability.
2. Gate Zero SHALL maintain continuously refreshed, per-provider, per-capability admission states with bounded freshness, canonical chain/head/hash checks, transport checks, fault-domain awareness, rate-limit/backpressure and circuit-breaker recovery. One eligible provider may serve a workload if its required correctness evidence is established; there is NO fixed configured-provider count, roster-size minimum, or simultaneous-health quorum. Independent corroboration is required only for operations whose evidence policy explicitly requires it.
3. The private Polygon node is the preferred native source and FIRST-CLASS FABRIC MEMBER; the external fabric is elastic, optional and capability-driven. Its stable provider ID is `polygon137-private-bor`; HTTP endpoint `http://10.77.1.77:8545`, WSS endpoint `ws://10.77.1.77:8546` (VPC only). Both transports belong to ONE logical provider identity/fault domain and MUST NOT count as two independent canonical witnesses. NO fixed 14-provider roster exists as a runtime prerequisite. Providers are discovered from configured authorized endpoints and dynamically admitted per capability. Each distinct upstream fault domain is counted once for corroboration; number of configured URLs never substitutes for correctness evidence. Never publish credentials or expose private RPC publicly.
4. Private-node preference is CONDITIONAL on native canonical readiness. If Bor is stale, the node SHALL be quarantined for current-state authority. A verified eligible external source MAY serve a scoped SHADOW workload as an explicit interim feed; its admission SHALL NOT certify the private node. No silent substitution or mixed-block route snapshots.
5. Asset Hunter SHALL continuously maintain its full pool census, publish verified graph deltas without a global 5,000/100-pool minimum, and continue lower-priority evaluation without starvation. APEX and SYMEN SHALL independently validate signed graph provenance, physical-pool uniqueness, block-pinned native quotes, exact protocol math, conservative all-cost Rust economics and SHADOW fork outcomes. No profitability gate belongs in the Hunter physical-pool census.
6. Route search SHALL preserve the canonical UniversalOpportunityRoute and 2–8-hop token-continuous cycles. Revisited tokens are valid when physical pools remain distinct. APEX C2 SHALL only follow a successful simulated C1 receipt, with independent state refresh and canonical two-block/TTL/idempotency constraints. SYMEN decisions remain independent.
7. Every admission, rejection, fallback and SHADOW outcome SHALL emit provider ID, workload capability, chain ID, block/hash, freshness, source/config/image identity, graph generation, trace ID and reason code. Missing or inconsistent evidence SHALL fail closed for the affected workload, not stop unrelated discovery.
8. Release authority remains HOLD until G0–G11 pass against compatible source commits, tested artifacts, immutable deployed image digests, actual runtime configurations and real read-only/fork evidence. Healthy ECS tasks are insufficient proof.

## Implementation and validation obligations

- Reconcile deployed RPC environment variables and secret references in APEX, Hunter and SYMEN with the single logical private-node ID. Do not infer endpoint admission from a configured URL.
- Verify HTTP JSON-RPC, WSS newHeads/log replay, ECS-to-private-node routing, authentication, canonical block hashes, pinned state and actual method-specific provider capabilities. Quarantine wrong-chain, stale, hash-disagreeing or incapable providers immediately.
- Test primary outage, HTTP 429, credential denial, WSS interruption, reorg, failover within the same pinned block and complete provider loss. No LIVE signing/broadcast or personal wallet connection is authorized.
- Reconcile parallel open PRs, tests and canonical README before merging; build pinned source and verify ECR digest/ECS task/runtime evidence after controlled rollout.

## Current evidence boundary

Historical ECS task definitions contain private-node HTTP/WSS addresses in APEX, private-node HTTP bindings in Hunter, and a private-node HTTP primary in SYMEN. That proves configuration presence only. Private-node synchronization, a variable number of authorized logical-provider identities, cross-service selection, economic execution and SHADOW certification are NOT established by this document.
