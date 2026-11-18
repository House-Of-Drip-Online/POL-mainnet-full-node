# OMEGA-G0-ADMISSION-001 — Operational admission and configuration contexts

Owner amendment: November 17, 2026. Governs Asset Hunter, APEX, SYMEN and their
Polygon node support. The final admission amendment supplied by the owner
supersedes the older recurring 25-observation wording in the same attachment.
CP-025 remains Fargate-only; older CodeBuild language is non-authoritative.

## Operational rule

Admit an individual workload as soon as at least one eligible provider has
current, independently corroborated canonical evidence and the required method,
state, transport and quota capabilities. Do not wait for all 14 inventory entries,
25 new observations, a complete census or 5,000 graph pools. Unknown or missing
capability is not a pass. Reject or defer only the affected workload.

Private Polygon state remains preferred when its readiness passes. The prior
private-only switch is a workload restriction, not a universal availability gate.
Validated interim providers are permitted under this amendment; they do not make
the recovering private node healthy. Rust hydration scheduling itself is offline
and performs no RPC. Its actual state reads remain governed by provider admission.
No public endpoint is activated merely by appearing in an inventory or profile.
Provider-specific budgets, authentication, block pins, C1/C2 timing, exact quotes,
complete-cost Rust economics and exact-payload simulation remain mandatory.

## Separate configuration planes

| Context | Configuration | Responsibility | May start an operational service? |
|---|---|---|---|
| BUILD | build-verification.json | Exact-source Fargate checks, fixture tests, image construction | No |
| COMMISSIONING | commissioning.json | Independent 25-observation and failure/recovery witnesses | No |
| RUNTIME | polygon-mainnet.json | Real chain-137 state and SHADOW operation | Yes, subject to existing readiness/authority |

Profiles are under config/profiles (modern/config/profiles in the node repo).
Operational values are injected through ECS or systemd and existing secret
bindings. The profiles are release inputs, not a new secret store. Build/test
profiles must never be loaded as operational configuration or copied into final
runtime images. Runtime images declare OMEGA_CONFIGURATION_CONTEXT=RUNTIME;
operational entrypoints reject BUILD, TEST, COMMISSIONING, build-source metadata,
NODE_ENV=test and commissioning-pass variables. Node service units declare the
same operational context. Explicit APEX/SYMEN runtime startup skips repository
.env defaults. Compiler/test stages remain separate from final runtime stages.

The APEX release contract and scripts/verification/verify-configuration-contexts.py
check ECS definitions before deployment. Each context has its own configuration
digest over the reviewed task inputs; build and runtime digests are not
interchangeable. Duplicate/shadowed environment bindings, operational RPC/secrets
in builders and build/witness inputs in runtime definitions are rejected. A
configuration-only pass grants no deployment or economic certificate.

Configuration context is distinct from execution permission: reading real
Polygon mainnet does not enable LIVE signing or transaction broadcast. Runtime
remains SHADOW and existing LIVE guards are unchanged. The profiles do not
change economic thresholds, quotas, route limits or timing windows.

## Commissioning and operational evidence

The existing application fabrics and private-node readiness gate do not contain
a recurring 25-pass operational counter in the inspected source. This amendment
makes that separation explicit; it does not pretend such a counter was removed.
The node commissioning_witness.py aggregates captured canonical-header gate
records independently. It cannot authorize operations, sign or broadcast. Its
header witness is not full native-state, WSS, fault-injection or economic
certification. Those additional witnesses remain required for their own release
claims. Missing or repeated/nonadvancing observations cannot manufacture passes.

Operational evidence must identify workload, provider, capability, block/hash,
freshness, selection/failover, latency, reason, configuration identity and owning
consumer. Certification evidence must additionally identify the witness profile,
source/image identity and integrity protection. Preserve independent APEX/SYMEN
admission, strategy, simulation and accounting authority. Expected, simulated and
realized results remain distinct.

## Dependency-ordered integration and verification

1. Freeze source heads and reconcile active parallel changes, runtime identities,
   provider inventory/secret bindings, IAM/networking and private-node readiness.
2. Verify each candidate provider from its actual workload network. Bind proven
   current, archive/log, WSS and fork capabilities separately. Preserve secrets.
3. Let admitted workloads proceed while census, external intake and node repair
   continue. Publish usable graph changes incrementally; no pool-count barrier.
4. Revalidate physical identity, 2–8-leg token/amount continuity, native protocol
   math, exact capital/quotes, Rust complete-net economics and calldata binding.
5. Certify exact fork outcomes, repayment/minOut/revert/freshness failures and
   receipt-gated C2 behavior independently for APEX and SYMEN.
6. Acquire versioned source artifacts; build/test on Fargate; reconcile immutable
   images/configurations; promote only a compatible SHADOW release set; read back
   every runtime. Preserve a complete release manifest and rollback set.
7. Run commissioning/recovery witnesses separately and monitor sustained operation.
   A witness is not an operational observation-count prerequisite.

## Implementation boundaries and unresolved evidence

This change implements context profiles, operational startup guards, .env
isolation and a separate header-witness aggregator. Existing native readiness,
provider selection and economic controls remain authoritative. It does not by
itself establish a fully inventoried/probed 14-provider registry, validated
interim endpoints, complete per-method p50/p95/p99, all WSS/reorg/failover cases,
source-matched deployment, continuous publication or complete SHADOW economics.
Those require actual source integration and measured runtime artifacts; all
unverified claims remain HOLD. A healthy process or a passing fixture suite
cannot substitute for G0–G11 runtime evidence.
