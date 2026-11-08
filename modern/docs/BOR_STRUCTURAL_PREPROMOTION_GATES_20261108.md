# Bor full-snapshot pre-promotion structural acceptance

**Source release audit:** 2026-11-08. This document describes NEW source gates; the active host is pinned to an older immutable restore release until explicitly promoted under release governance. It is **not** evidence that the active restore has completed.

## Safety changes

1. `validate_snapshot_plan()` requires Polygon chain ID 137; 2–16 uniquely named components; the first block begins at genesis zero, all subsequent `firstBlock` values equal the predecessor's `lastBlock+1`; no overlap or gap. Each component requires bounded numeric compressed/uncompressed sizes, HTTPS without credentials/fragments, and pinned strong ETag syntax.
2. During post-download merge, `progress.json.status` becomes `MERGING` instead of silently reusing a stale `RESTORING` download update. `processedEntries` and `checkedAt` are refreshed during the idempotent move. This does not modify Pebble or consensus metadata.
3. `verify_ancient_layout()` checks the merged Pebble `CURRENT` file, requires a local nonempty `MANIFEST-n` pointer, and checks contiguous `headers`, `bodies` and `receipts` ancient `*.cdat` segments from index 0. No on-chain attestation is inferred. Missing fragments, malformed indices or manifest links prevent source promotion.
4. The monitor and recovery advisor accept `MERGING` as a distinct bounded recovery phase. Missing/invalid entries and stale merge heartbeats fail closed. No simultaneous second writer or ambiguous LIVE authority is ever started.
5. Signed source lock/transport ETag/local compressed SHA-256, complete extraction, structural verification and native Bor canonical-state validation are **four distinct evidence classes**. Success in one cannot substitute for another.

## Physical source inspection before completion

Read-only host inspection of staging components showed:

| Component | Physical ancient segment family | Observed index range | Internal gaps |
| --- | --- | --- | --- |
| Base | bodies | 0–767 | 0 |
| Base | headers | 0–22 | 0 |
| Base | receipts | 0–781 | 0 |
| Increment (partially extracted) | bodies | 768–843 at sample | 0 |

The observed **body index continuation is clean at the sample time**, and top-level component filenames had no overlap. These counts do **not** prove the complete increment, index contents, hash integrity, canonical consensus state, or historical `eth_call` archive capability. The complete restored dataset must satisfy the same source structural gate before native startup, and independent RPC/head checks afterwards.

## Verification

Executed a memory-only source regression suite using the host's installed Python under unprivileged `omega-rpc`, with no writes to node state and no service changes:

- 7 new structural lock/manifest/ancient/merge tests: PASS.
- 5 incumbent full-snapshot streaming, resume, unsafe tar and conflict tests: PASS.
- 7 enhanced monitor tests including `MERGING` telemetry: PASS.
- 10 enhanced recovery-advisor tests including fresh/stale `MERGING`: PASS.
- Total: **29 passing tests in the targeted source regression suite**.

GitHub Actions currently fails almost immediately on `main` and feature branches before test execution, and thus is **not** an independent positive CI attestation for this change. The source test proof is limited to the separately run memory-only suites.

## Blocking release gates

- Do not change the active pinned restore source in place while its LZ4 worker and range downloads are progressing. No competitor may access the same Pebble database with write authority.
- A governed node update from the current source SHA requires an immutable build/release and rollback evidence, non-root administrative authority or separately documented narrow owner exception, and confirmation that the active stage has a safe transition point.
- A source-only PASS is not deployed proof. Post-restore Bor process must start with valid ancient paths and independent header/state parity, keep chain ID 137, expose the bounded private gateway with read-only methods, and pass warm/cold restart + consumer-path tests.
- For full historical archive requirements, `gcmode=full` with bounded PBSS state history **does not** establish full old-state archive. Evaluate supported historical ranges, or provision an isolated explicitly sized PBSS archive path.

The data plane never gains signing or mainnet broadcasting authority by passing node restoration gates.
