# OMEGA — Four-repository source-first closure / executable-graph restoration
**Date:** 2026-11-17. **Chain:** Polygon 137. **Execution posture:** SHADOW only, LIVE signing and broadcasting OFF.
**Ordering directive:** (1) governing source and tests; (2) governing canon and release contract; (3) isolated pinned-source Fargate tests + builds; (4) configuration-safe deployments; (5) current native economic proof. Neither a code commit nor a healthy container constitutes a completed economic gate.

## Final architecture invariant
Dedicated Polygon private node (Bor live HTTP 8545, WS 8546, Heimdall) is the authoritative Polygon native-hydration provider for Asset Hunter. Hunter discovers ALL viable physical liquidity pools persistently, maintains independent root factory cursors, and immediately publishes a signed, fresh and native-verified executable-ready subset; external market signals may continue during node outages but have NO native execution authority until independently verified. APEX and SYMEN independently rehydrate the signed graph at their own current canonical blocks and build independently priced executable edges. There is no 100, 1,000, 5,000 or 16-root global graph admission floor.

APEX owns its canonical progressive UniversalOpportunityRoute lifecycle. S0–S9 are internal checkpoints only. Closed swap cycles support 2–8 hops, distinct physical pools, valid token revisits, amount and token continuity and exact block/hash native quotes. Canonical Rust owns X* and complete-cost net; gross spreads do not authorize a transaction; zero or negative net never passes even when minimum breaker is configured zero. Top-50 staging requires positive independent successful plan and calldata build evidence for EVERY occupied slot; failure/absence cannot become success by default. C2 is receipt-scoped, independent post-C1 state, idempotent with canonical two-block activation and TTL. SYMEN never needs APEX lifecycle, graph, or receipt; SHADOW should not require a LIVE wallet session.

## Verified source corrections this integration cycle
- Hunter main already merges independent external advisory intake while private native RPC is unavailable; advisory source state and verification queue are durable, not executable. Private-only native RPC binding was later added and must be enabled in the next validated runtime task, with private-node unhealthy -> native work deferred, not silently sent to public RPC.
- APEX source `backend/logistics/src/opportunity/UniversalOpportunityRoute.ts` independently asserts distinct physical pools and closed R2–R8 exact quote cascade. `backend/logistics/src/opportunity/StagedRouteMaterializer.ts` now preserves originating C1/C2 lane after concurrent Codex edits.
- APEX `backend/logistics/src/economics/EconomicAuthority.ts` now requires an explicit per-opportunity `StagingBuildEvidence { planBuilt, calldataBuilt }` map in `stageTop50EconomicAdmissions`, with no default success when missing, and refuses zero-net staging; test file `backend/logistics/tests/EconomicAuthority.test.ts` contains the corresponding regression. Build evidence must reflect ACTUAL built plan/call outcome, not an assumed boolean.
- SYMEN `src/symen/production_runtime.py` economic readiness now treats the agent-wallet session as a LIVE-only requirement; SHADOW economic evaluation remains subject to signed-source/native/evidence governance but is signer-independent. `tests/test_readiness_evidence_latency.py` exercises SHADOW vs LIVE. A previously merged source change rechecks operational SAFE/HALT after admission.
- Node source repo `POL-mainnet-full-node` contains corrected HTTP 8545 / WS 8546 listener topology and a reviewed version of the AWS template, but the live CloudFormation stack output still incorrectly advertises WS 8545. Do not update the node stack with unreviewed instance/volume replacement.

## Release configuration / authority locks
| Owner | Key | Required state |
|---|---|---|
| Node | HTTP / WebSocket | 10.77.1.77:8545 HTTP and 10.77.1.77:8546 WebSocket, respectively; real service health/readiness proven |
| Node | snapshot and storage | preserve both existing 16 TiB EBS volumes, nested live Bor bind, completed independent snapshots and rollback path; never reset/delete/reformat on assumption |
| Hunter | ASSET_HUNTER_NATIVE_RPC_PRIVATE_ONLY | true, bound exclusively to http://10.77.1.77:8545 for all native hydration |
| Hunter | ASSET_HUNTER_EVENT_WSS_URL + opt-in | ws://10.77.1.77:8546 and explicit approved RFC1918 plaintext opt-in only after verified secure scoped SG and node WS readiness; replay required |
| Hunter | Archive historical | independent method-and-block verified archive capability; no invented source or silent fallback; one healthy per operation if allowed |
| APEX worker + ingress | POLYGON_RPC_HTTP_PRIMARY | http://10.77.1.77:8545, never on WS port |
| APEX worker + ingress | POLYGON_RPC_WSS_PRIMARY / OMEGA_WS_RPC_URL / POLYGON_WSS_URL | ws://10.77.1.77:8546, not 8545 |
| APEX worker + ingress | OMEGA_DISCOVERY_MIN_PHYSICAL_POOLS_FOR_SHADOW | 0; route admission depends on per-pool proofs, not global counts |
| SYMEN | signed source and readiness | independent current signed Hunter version, durable consumer ACK/replay, native economic authority, no APEX readiness dependency |
| All | execution authority | LIVE, signing, broadcasting must remain disabled; no implicit arming with config or deployment |

## Verification / release decisions
1. Read and reconcile current exact main head for all FOUR repos; account for concurrent Codex merges. Any source change after a release source pin invalidates claims of exact-main deployment and requires a new evaluated release candidate. Docs-only drift can be assessed separately with explicit exact file diffs, never asserted to be identical main.
2. Code tests first: Hunter full TypeScript & Python suite, native-only provider binding and advisory outage safety; APEX source/docs tests, canonical route R2–R8, Rust/cost parity, success-only Top50, C1/C2; SYMEN independent admission, SHADOW wallet-free economics and LIVE signer hold; node client/CloudFormation safety and read-only RPC probes.
3. Signed CodePipeline versioned artifact + content tree readback -> isolated Fargate full tests -> immutable ECR digest -> evidence bucket. All source/docs require actual pass, no skipped verification disguised as success.
4. Promote only compatible worker/ingress/dashboard artifacts with exact manifest. Inspect ECS task definition diff (environment, secrets, mount points, EFS, role, resources, image, source labels), circuit breaker, service rollout, running task digest and business-level telemetry. Never overwrite a concurrently registered revision with stale derived `IMAGE_DIGEST`.
5. Canary: node chain 137 block/hash agreement and full native RPC readiness; Hunter fresh pool quote publication; independent APEX/SYMEN signature acceptance and currently executable physical pools/edges. Repeated nonzero output depends on real qualifying liquidity, never fabricated counts. Capture all typed rejection waterfall and SHADOW positive-net route proof if actual market offers it.
6. LOCK if node stale/trie-damaged, current executable edges remain zero without native proofs, no independent archive capability, conflicting shared signer nonces, unmerged overlapping PRs, evidence drift or failed tests. LIVE only after later separate owner authorization and receipt-based net accounting.

## Latest observed pre-certification blockers
- Private Bor healthy service process but stale execution state (latest readback node lag ~16,533 blocks; no trie-error matches in recent sample); executionAuthorized=false. This can be progress toward sync, NOT health.
- Hunter ECS revision 193 has passed source image provenance and healthy rollout; producer native `PROVIDER_AVAILABILITY_LOST` persists. External intake works independently and correctly defers native execution.
- APEX executor rev204 + ingress rev16 remain older image; newer tested candidate Fargate image build failed because source at its PIN did not include a later required source/canon sync file, demonstrating why exact current source docs must be rebuilt. Build from final current source.
- SYMEN rev104 does not contain later readiness/canon and wallet-independence edits; requires immutable built candidate before SHADOW promotion.
- Node CloudFormation `PrivateWebSocket` output still 8545 despite actual WS listener 8546. Change-set must be strictly non-replacing before execution.
- No actual positive-net settlement or currently executable graph revival certified.

## Final evidence records
Per release keep: source sha/tree; pipeline execution and S3 version; passing tests; provenance archive/manifest; ECR digest; ECS revision and running task digest; exact env diff, LIVE-off status; health and native-data readiness; Hunter signed publication hash; APEX and SYMEN independent ACK, native quote blocks, current physical pool count, directed edges, valid 2–8 routes, staged successful builds, SHADOW gas/flash/net proof and typed reasons. NO fabricated profits.
