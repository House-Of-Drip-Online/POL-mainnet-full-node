# POL-NODE-ANSIBLE — Polygon Node Reuse / Compatibility Gate

**Evidence date:** 2026-10-11  
**Status:** LEGACY_SOURCE / NODE_NOT_DEPLOYED_AND_UNVERIFIED  
**Authority:** Infrastructure provenance only. No trading, discovery registry or signing role.

## Why the repository can be reused

Reuse its directory boundaries, deployment history, snapshot workflow principles, network topology and infrastructure knowledge. Do **not** assume the existing images, install commands or scripts will work with today's Polygon consensus execution requirements.

## 2026 compatibility requirements

- Review the maintained upstream execution client [0xPolygon/bor](https://github.com/0xPolygon/bor), its supported releases, mainnet chain ID 137, APIs and node pruning rules.
- Review the maintained consensus client [0xPolygon/heimdall-v2](https://github.com/0xPolygon/heimdall-v2), mainnet genesis/bootstrap requirements and snapshot compatibility.
- Replace obsolete Ubuntu/base images, package versions, Docker Compose syntax, static peer lists and old snapshot sources only after exact image digest/source pinning.
- Validate hardware cost (official Bor README cites 1 TB minimum disk for mainnet; live needs depend on dataset and pruning), EBS growth, ingress and egress, backups, patching and monitoring. **Open-source software is free; cloud node operation is not.**
- Expose node RPC only to private governed VPC consumers, use least-privilege/deny-write policies and authorization. Never publish an unrestricted open relay or production signer.
- Establish real full sync, block/hash parity with independent providers, archive versus nonarchive capability tests, WSS continuity, log-range acceptance, RPC cost and reorg behavior.

## Current MAEVN decision

No functioning self-hosted node was verified in EC2 inventory for AWS us-east-1 on 2026-10-11. Preserve the working third-party provider set until a fresh node proves stable; do not add a node to the 19 verified HTTP/WSS connections by counting source files.

## Go/no-go economic gate

Deploy only if `monthly_commercial_RPC_cost + expected_avoided_retries + operational_value` exceeds `EC2 + EBS + egress + monitoring + backups + staff_time + failure_risk`, based on actual 7-day per-vendor billing and traffic. Avoid speculative savings.

## Documentation standard

Follow MAEVN Documentation Governance Canon v1.1 in each consumer repository. Preserve historical README titles and source authority; rewrite setup instructions *in place* only after a clean, tested version-pinned replacement exists. The main branch instructions remain historical until this review is merged.
