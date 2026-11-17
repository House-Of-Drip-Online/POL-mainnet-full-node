# OMEGA — Four-Repository Source → Image → Infrastructure → Runtime Discrepancy Audit
**Date:** 2026-11-17 (21:15 UTC window, snapshots vary by service)
**Artifact:** OMEGA-FOUR-REPO-PROVENANCE-AND-RELEASE-AUDIT-20261117
**Classification:** Read-only evidence/release reconciliation. NOT a new overriding canon, merge approval, infrastructure change set, economic certification or LIVE authorization.
**Chain:** Polygon PoS 137 | **AWS region:** us-east-1 | **Execution posture:** SHADOW only.

## Executive decision
**YES — new application images and coordinated infrastructure configuration changes are required.** Hunter was newly advanced to ECS revision 193 during this review; that is material progress, but deployed source is still six commits behind the observed Hunter `main`. APEX executor and governed ingress are 68 GitHub commits behind current `main` and have incorrect WebSocket port configuration and a legacy discovery setting. SYMEN worker is 22 commits behind `main`. The independent Polygon-node CloudFormation release is 11 repository commits behind the latest node `main` relative to its readiness monitor; its actual stack source parameter is an *additional* earlier commit. The node is running, syncing and fail-closed, NOT chain-ready. Signed market-state consumption and positive-net SHADOW settlement are unproven.

Do not confuse: (1) source committed; (2) focused tests passed; (3) immutable image built; (4) ECS service updated; (5) accurate current native output; (6) source/runtime/economic certification. These are independent gates.

## 1. Directly inspected GitHub-to-running-image matrix
The `main` SHAs below are point-in-time readbacks **before this audit document is committed**. Later concurrent Codex merges require a new freeze/readback. GitHub ahead counts include documentation and tests; they do not directly measure runtime functionality.

| Component | Observed main SHA | Last observed runtime source SHA | Deployed task / immutable image digest | Ahead | Decision |
|---|---|---|---|---:|---|
| Hunter worker | `431157c3f911cfc5d24f8eda3ff6cc544d7e04f5` | `20b069344a88ef5871b1b7ac55ce6aaf713a6cab` | `asset-hunter-prod:193`, `sha256:dc24334852116b6b3a997d9947c925cc553d201131204066dbc0267170d886d8` | 6 | **Rebuild after merging and testing remaining native-RPC/root-policy commits** |
| APEX executor | `c4ce87d8b3dde95d32bab75b00e55cecec1fce15` | `36c6b33fd88238805ac416e252ab9ef7a7ad82e9` | `apex-omega-shadow:204`, `sha256:67bc8ed21ecd48e91fa75bbafd45350a8f8f77e06a697141e54cc159d8331adb` | 68 | **Mandatory new image/task revision** |
| APEX governed graph ingress | same APEX `main` | `36c6b33fd88238805ac416e252ab9ef7a7ad82e9` | `apex-omega-governed-graph-ingress:16`, same executor digest | 68 | **Mandatory matching compatible image/task revision** |
| APEX dashboard | same APEX `main` | `5a4afd5c612b20e709d91ce5e8396bf795c43db9` | `apex-omega-dashboard:11`, `sha256:2be95e8a4b7afbd7e3f93094383790bd31bf95d87972d77954378d6c828295f4` | not independently compared | **API/schema compatibility and telemetry source audit; update if newer dashboard changes are required** |
| SYMEN worker | `7ab6d1081aab923d35aac719bf3082e10c6fd50e` | `872234585e0811c3ca3ab006ca4866ab0f1500bb` | `symen-prod:104`, `sha256:369b7ca1fe129cefa82b3357dd74b9db2e750cf69fb6e63869ec366c6bfa3e26` | 22 | **Mandatory new tested worker image/task revision** |
| SYMEN dashboard | same SYMEN `main` | `92bf62985a6ff6d7d30365e8fc88d69f71edff8a` | `symen-dashboard-bootstrap:27`, `sha256:420a51f9f483621d863710cfa0c043bde3b998f4344b27cf6c54d79d25349b8d` | not independently compared | **API/source/monitor parity check; rebuild only as needed** |
| Polygon node | `e039b051573cc273e1979fd25da49880e52c4a7c` | readiness monitor declares `8f12dc81fe01648056051b87adb285e2a6fbd7f2`; CloudFormation and EC2 tag use `d961c2c9b0c28f2e99b1747e4786451e0b485e3f` | EC2 `i-0e9c908e9994086e8`, no ECS image | 11 vs readiness SHA | **Controlled source / stack / installed-service convergence; do not replace EBS or bootstrap into the live data directory** |

All six currently running ECS services have desired=running and primary rollout COMPLETED. Actual running ECS container digests match the pinned task definition images. This is **deployed-image identity parity**, not current-main source parity.

## 2. Additional critical AWS infrastructure discrepancy — node stack OUTPUT IS WRONG
- Actual EC2 private listeners: HTTP JSON-RPC `10.77.1.77:8545`, WebSocket JSON-RPC `10.77.1.77:8546`. Both services running; both readiness endpoints returned HTTP 503 in the earlier safety canary while Bor not ready.
- Actual node SG `sg-04bb9ebae98da4c87` permits 8545 and 8546 only via four known security-group source entries, with no CIDR sources for these ports in inspected rules. That is a scoped private SG ingress, not proof of active subscriptions.
- CloudFormation stack `omega-polygon-137` remains UPDATE_COMPLETE, last updated 2026-11-10, parameter `SourceCommit=d961c2c9b0c28f2e99b1747e4786451e0b485e3f`, and **output `PrivateWebSocket=ws://10.77.1.77:8545` is wrong**. The current-node repo template has corrected the WebSocket output to 8546 and added SG rule, source-provenanced separate proxy service, and bootstrap integration, but the live stack has not received that template.
- Do not update the live stack directly with an unreviewed change-set: its live node now has 16-TiB live and recovery volumes, while repo templates and historic provisioning can carry different assumptions. Require a no-replace/no-detach/no-erase diff, separate live-vs-template parameter audit, source archive pinning, and rollback evidence.
- Installed node source files may be ahead of the stack's SourceCommit. Capture per-file SHA256 and compare with current source before promotion. `modern/rpc_ws_proxy.py` was recovered from installed source into main and 8 security/readiness tests passed; `modern/aws/node.yaml` passed AWS ValidateTemplate, not stack update.
- Bor latest inspected readiness `FAIL`: 18,297 blocks behind, `LOCAL_HEAD_STALE`, `LOCAL_SYNC_INCOMPLETE`, `NODE_LAG_LIMIT_EXCEEDED`, `executionAuthorized=false`. Heimdall healthy; latest sampled Bor trie errors zero. A catching-up process is NOT admissible current-state provider.
- Memory/IO: m7i.4xlarge, Bor configured ~8-GiB cache, 36-GiB MemoryHigh /44-GiB MemoryMax; two 16-TiB gp3 encrypted volumes provisioned at 16k IOPS and 1000 MiB/s each. Prior high IO PSI and heavy recovery-device activity require sustained benchmarks, not an assumed hardware shortfall. Node DB/EBS snapshots are recovery assets, never substitutes for exact-block executable graph state.

## 3. Deployed configuration problems, explicit remediation owners
| P | Owner | Observed state | Required next release behavior | Release safety |
|---|---|---|---|---|
| 0 | APEX executor + ingress | All `POLYGON_RPC_WSS_PRIMARY`, `OMEGA_WS_RPC_URL`, `POLYGON_WSS_URL` = `ws://10.77.1.77:8545` | Point actual WS aliases to `ws://10.77.1.77:8546`; HTTP stays `http://10.77.1.77:8545` | Validate WS handshake, `newHeads`, filtered logs, reconnect/replay after node canonical readiness, private VPC/SG controls |
| 0 | APEX executor + ingress | `OMEGA_DISCOVERY_MIN_PHYSICAL_POOLS_FOR_SHADOW=100`; old runtime also reports `rootsRequired=15` | New source renders global pool count observer-only or zero; source-verified root cardinality=16 where relevant | No 100/1,000/5,000 pool hard startup barrier; never fake a native edge |
| 0 | Hunter | Main 6 commits after image 193, provider/native policy touched | Align next immutable Fargate image and task with latest reviewed merged source | A version label or healthy ECS service alone is insufficient |
| 0 | Hunter | Primary and historical `http://10.77.1.77:8545`; event WS URL absent; `PUBLIC_RPC_URLS_JSON=[]`, rotation false; no second RPC URL configured | Separate independently qualified archive/root/backfill, native current read, advisory and event lanes; gate event stream on node readiness | Do not treat historic/third-party advisory data as execution-grade native state |
| 0 | Hunter | New `ASSET_HUNTER_NATIVE_RPC_PRIVATE_ONLY` code may restrict native calls to single private URL; flag absent in deployed task, and node is not ready | Explicitly decide whether native state must be private-only (halt when down) or can fail over only to independently verified canonical native-capable endpoint. Preserve 1-healthy-per-operation Provider Fabric doctrine for allowed lanes | **Policy conflict** with earlier capability-aware native fallback; do not set flag blindly or silently bypass private-node preference |
| 1 | SYMEN | Worker rev104 remains independent signed-source admission pending | Deploy final source only after independent signature/cursor/ACK/native strategy tests; do not wait on APEX | SHADOW remains wallet-independent and LIVE OFF |
| 1 | APEX + SYMEN dashboards | Running older source and may read old telemetry | Verify backend schema compatibility, current executable pool/edge counters, typed rejections, and provenance | Update only if required by the source/schema changes, test against deployed worker APIs |
| 1 | Provider/node | 8546 SG allowed but CloudFormation output still 8545 | Patch current stack desired template/output through reviewed non-replacement change set | No chain-data volume detach, delete, shrink or instance replacement |

## 4. What conversation designs are already in source versus still unproven
| Requirement | Audited disposition | Additional implementation/deployment proof |
|---|---|---|
| One progressive `UniversalOpportunityRoute` object, S0–S9 internal checkpoints | APEX current main has route schema, construction handoff and new docs | End-to-end authority transition and source-to-image tests; do not create parallel production schema |
| Strict closed R2–R8, distinct physical pools, token+amount continuity, valid token revisits | APEX source updated (construction, RouteEnumerator, materializer), targeted 19/19 tests on older pinned main SHA; later main merged fixes | Re-run **final HEAD** full tests, fork and real-native graph; deploy immutable executor+ingress |
| Exact snapshot/hash, quotes, calldata and Hunter source lineage | Mixed existing source and governing directives; structural boundary tightened | Verify every actual route hop has independent exact-block native state and compatible calldata plus signed Hunter provenance, not merely a `blockNumber` |
| Rust X*, lender capacity, <=15% smallest route-pool TVL, fully costed net >0 | Source economics guard and Rust adapter changes after old deployed image | Independent Rust math/TS reconciliation, native protocol fees once, full-cost net ranking, lender probes, negative/zero-net rejection with breaker=0 |
| Net-ranked Top-50 **successful build** staging | Bounded controller/Top50 structures exist; staging success-only behavior not certified | Distinct success-only slot accounting, ranking proof, typed failure metrics, real graph case |
| C1/C2 receipt-bound cycle isolation, TTL and two-block C2 activation | Main contains C2-lane and route changes; selected prior tests passed | Fresh merged-source C1 receipt/C2 nonce/retry/NO_OP tests and SHADOW traces |
| Hunter 16 independent roots, continuous all-census inventory, immediate qualified-subset publication | Census 218,117; 6/16 roots complete in earlier evidence; source root-cursor and event work open | Independent root cursor progression, durable replay, verified native subset emission without census completion gate |
| Event-driven heads/logs, durable journal/gap replay, hot/cold hydration | Secure private WS watcher source + tests exists; node gateway code recovered. Production Hunter event WS absent | Deploy and test actual event subscription, canonical head chain, gap replay, bounded memory/queue fairness and reorg invalidation |
| SYMEN independently signed Hunter admission and graph, SHADOW economics | Current source has improvements, 22 commits ahead of worker; many admission/economic PRs still OPEN | Independent worker ACK/strategy/native graph test without APEX or LIVE wallet |
| Canon/source synchronization | Shared docs, CI workflow and machine-checkable desired configuration committed | Verify CI executes and is required for merges; provenance trace to actual image and ECS after every change |
| Private Bor snapshots and graph snapshots | Recovery volumes and existing APEX block-hash caches observed | Verify EBS snapshot consistency+rollback; bounded graph snapshot retention keyed by canonical block/hash; no stale cache promotion |
| Actual economic production, LIVE settlement | No new complete positive-net SHADOW trace or settled surplus verified | Real native edges, valid routes, cost-correct fork proof, independent agent-wallet authorization, actual on-chain receipts |

**An open PR is not `main` and a main implementation is not a deployed image.** At the inspection, 26 Hunter PRs, >=35 APEX PRs (search page cap), 22 SYMEN PRs and 2 Node PRs remained open. In particular Hunter signed readback #196, external discovery #192, provider-quota #184; APEX route ranking #448, execution repayment #439, SHADOW trace #446 and other economics; SYMEN native valuation #161, cross-pool #164, independent journal/settlement PRs must be audited for overlap. Do not mass merge; compare touched paths and preserve one authority per computation.

## 5. Reproducible deployment matrix — work **to push to deployment**, not already deployed
**Batch A — Node safety / authoritative data**
A0 current EC2/EBS preservation and independently compared source; archive capable provider method probes; 16 root cursor evidence; current node lag/head/peer/IO trends and no recurring trie failures. Record all required rollback evidence. A1 apply non-replacement CloudFormation source/output reconciliation **only after change set verification**, with separate HTTP 8545 / WS 8546 and explicitly limited client SG. Never run bootstrap against active Bor chain DB. A2 after canonical node is fresh, prove WS subscription/reorg and current native `eth_call`, historical `eth_getLogs` on archive lane.

**Batch B — Hunter tested image**
B0 reconcile newest Hunter main with 6 source/docs commits, private-only native policy, historical fallback and signed publication; test final merged main (TS + exact protocol adapters + EFS census migration, read-only). B1 source-provenanced Fargate image to immutable ECR digest, new task definition, canary before production; WS 8546 activation conditional on A2, no public fallback silently granting native authority. B2 verify perpetual Hunter census, no arbitrary pool-count gate, typed failures and fresh signed subset publications.

**Batch C — APEX executor+ingress**
C0 reconcile current-main 68 commits, open overlapping PRs, exact R2–R8, Rust and net Top50, C1/C2, full source+contracts+fork tests (a prior 1,090-executed-test Fargate PASS was pinned to older `3b68e1e2`, not current main). C1 build a single compatible certified executor image pinned to final SHA and new ECS task revisions for **both** shadow executor and governed ingress; set all three WS aliases to 8546 and remove obsolete global 100-pool gating. C2 demonstrate block-pinned native graph `accepted -> hydrated -> authorized`, no stale false positive, 25 trace cycles, typed economically rejected outcomes. Dashboard gets schema-compatible update as needed.

**Batch D — SYMEN independent worker**
D0 reconcile 22 ahead commits + overlapping admission/strategy/settlement PRs, verified signer provenance and cursors, no APEX dependence; run full tests/fork where necessary. D1 Fargate image and task revision, validate independent Hunter ACK and current strategy graph without APEX and without wallet in SHADOW. Dashboard update only if APIs/schema demand it.

**Batch E — Strict provenance and release acceptance**
One immutable release manifest per active service: `repo`, `main SHA`, `Git tree`, `source archive S3 version`, `test artifact`, `ECR digest`, `task definition ARN`, `running image digest`, `RPC address/method capability`, `mode`, `publication block/hash`, `consumer ACK`, `currently executable physical pool+edge count`, `fork result`, and (only when separately authorized) `settlement receipt`. Reject any missing link.

## 6. Certification exit / grade
- R0: all concurrent Codex source changes frozen, conflicts reconciled and authoritative docs updated on the SAME final release commits.
- R1: independent chain137 canonical current state across private+verified capability provider, node readiness PASS and protected DB/snapshot rollback.
- R2: all applicable workload lanes have independently tested endpoints/capabilities; Hunter continuous qualified data and signed fresh publication.
- R3: exact ECR/ECS digest/readbacks for Hunter/APEX executor/ingress/SYMEN, correct 8545 HTTP / 8546 WS usage, no arbitrary minimum pool gate.
- R4: independently ACKed Hunter publication by APEX and SYMEN, truly native-executable graph with precise exclusions, when valid liquidity exists.
- R5: cost-correct native 2–8 route construction, Rust X*, net Top50 successful-builds, exact calldata and repeatable SHADOW simulation (honest zero if genuine market has no positive-net route).
- R6: LIVE remains separately authorized; never infer signer/wallet authorization from successful SHADOW.

**Engineering scores (expert estimates, NOT benchmarks):** governance/architecture target 95–98/100; current source correctness 85–92 for inspected path subsets; deployment source-to-main parity 35/100 due major APEX/SYMEN drift; private-node canonical readiness ~20/100 (lag declining, still FAIL); end-to-end economic readiness ~30/100, no completed SHADOW evidence. Do not average these into a false certification grade. NO ACTUAL NET SURPLUS IS CONFIRMED BY THIS AUDIT.

## 7. Non-negotiable safety
- No destructive snapshot/db rewrite, volume deletion, instance replacement, unreviewed SG exposure, signing or broadcast enablement.
- Preserve always-on Hunter external **identity/advisory** intake even if native source unavailable; advisory data alone never certifies executable prices.
- At least one verified provider **for the specific operation** rather than an arbitrary multiple-provider quorum. If the owner chooses private-only native reads, stale private node must truthfully block native readiness until healthy; distinct external/archive lanes may still progress.
- APEX and SYMEN remain separate consumer and strategy authorities. C2 is a reaction **cycle**, not a swap leg.
- All reported counters are actual measured values; zero native executable opportunities must not be replaced with synthetic positives.

## Direct AWS audit records
ECS DescribeServices, DescribeTaskDefinition, DescribeTasks (running image digests); CloudWatch FilterLogEvents; SSM node `/run/omega-polygon/readiness.json`; EC2 DescribeInstances/DescribeSecurityGroups; CloudFormation DescribeStacks; GitHub compare base↔main for four repos; relevant source files. Log window and GitHub merge activity are dynamic: **read back again immediately before any release**.
