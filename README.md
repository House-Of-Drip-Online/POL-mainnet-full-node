> **Official four-repository doctrine (2026-11-18):** [OMEGA institutional ownership, runtime, graph, wallet, SHADOW/LIVE and W0–W10 certification contract](docs/canon/OMEGA_OFFICIAL_FOUR_REPOSITORY_DOCTRINE_20261118.md). This governing target does not certify deployed images or authorize LIVE.

> **OMEGA-SOURCE-FIRST-FOUR-REPO-EXECUTABLE-RECOVERY (2026-11-17):** [Coordinated source-first executable recovery and SHADOW release gate](docs/engineering/OMEGA_SOURCE_FIRST_FOUR_REPO_EXECUTABLE_RECOVERY_20261117.md) governs four-repository source, canon, immutable build and native-output evidence. Its acceptance does not certify current executable edges or enable LIVE execution.

> **2026-11-17 four-repository source/image/runtime audit:** [OMEGA verified deployment discrepancy and certification matrix](modern/docs/OMEGA_SOURCE_TO_DEPLOYMENT_GAP_AUDIT_20261117.md). This is a dated *evidence snapshot*, not a silent canon override or deployment certificate. Latest-main source, immutable ECR/ECS image provenance, exact 8545 HTTP/8546 WS configuration, Bor stack drift, independent Hunter/APEX/SYMEN admission and economic proof must be reconciled before SHADOW promotion; LIVE signing remains disabled.

> **OMEGA 2026-11-17 maintenance and R2–R8 economic checkpoint:** [Verified node/route source changes and remaining production certification gates](modern/docs/OMEGA_LIVE_MAINTENANCE_NODE_ROUTE_CLOSURE_20261117.md). Preserves historical image evidence, independent Hunter/APEX/SYMEN authority, canonical-chain readiness and LIVE-off safety. Source/test commits do not automatically confer current-image parity or settled-profit certification.

# OMEGA Polygon 137 full node

The supported deployment is in [`modern/`](modern/README.md): Bor 2.11.1,
Heimdall-v2 0.13.2, Ubuntu 24.04, AWS EC2, encrypted retained EBS, private
read-only HTTP/WebSocket RPC, and SSM administration.

Start with the [operation runbook](modern/RUNBOOK.md),
[target and acceptance criteria](modern/TARGET.md), and
[AWS template](modern/aws/node.yaml). Source checks do not establish live
synchronization. Runtime readiness remains closed until canonical-state checks pass.

**Do not deploy the historical Docker, Ansible, Vagrant or snapshot files below.**
They contain obsolete 2021 clients and configuration. They remain only as source history.

<details><summary>Historical README — unsupported</summary>

# Deploy matic-mainnet-full-node

> **CURRENTNESS WARNING — 2026-10-11:** This repository is a historical Polygon node deployment source, **not an operating, synchronized, production-certified Polygon RPC node**. Ubuntu 18.04, pre-V2 Heimdall, and old Ansible/docker-compose commands are historical, not certified 2026 deployment steps. Do not deploy its commands without the compatibility review in [NODE_READINESS_2026-10-11.md](docs/NODE_READINESS_2026-10-11.md). The original instructions below are retained for audit/history.


Push button deployment of Matic/Polygon mainnet full node

Polygon is a protocol and a framework for building and connecting Ethereum-compatible blockchain networks. Aggregating scalable solutions on Ethereum supporting a multi-chain Ethereum ecosystem.

This repo contains an Ansible playbook to deploy the heimdall and bor components.

# Requirements

System specs for the full node

Minimum system requirements are as follows:

16 GiB of memory
4 core CPU (t2 xLarge)
Minimum 150GB disk (make sure it is extendable)

OS

- account with sudo access to perform tasks as root
- internet access

# What is managed

All tasks required to run heimdall and bor in a docker-compose setup are managed.

- manage workspace
- prepare the node for docker deployments
- manage docker-compose config
- build docker images
- download snapshots for heimdall and bor to get in sync faster then from scratch
- extract snapshots to heimdall and bor data dir
- manage heimdall and bor docker compose services

# Usage with vagrant (development)

To deploy a development environment

Manage Ubuntu 18.04 VM with vagrant and provision Polygon Mainnet full node with Ansible

```sh
vagrant up
```

On first boot this will provision the instance.

If you want to provision again and run the playbook run:

```sh
vagrant provision
```

# Usage on a clean install

Tested with Ubuntu 18.04

Clone this repo
```
git clone https://github.com/mawi001/ansible-matic-mainnet-full-node.git
```

Install Ansible
```sh
./run.sh
```

Run Ansible playbook to deploy to localhost

```sh
cd ansible
ansible-playbook -v -i hosts deploy.yml
```


## Sovereign admission alignment

This repository remains an independent project/build boundary. Shared trust and interoperability semantics are documented in [`docs/SOVEREIGN_ADMISSION_ALIGNMENT.md`](docs/SOVEREIGN_ADMISSION_ALIGNMENT.md). Sovereign alignment does not merge repositories, builds, deployments, security domains, or runtime authority.


## Source authority matrix

Source ownership, active versus archival loci, external authority boundaries, and known divergences are documented in [`docs/SOURCE_AUTHORITY_MATRIX.md`](docs/SOURCE_AUTHORITY_MATRIX.md), governed portfolio-wide by `House-Of-Drip-Online/-MAEVN-HOLDINGS/topology/APEX_SOURCE_AUTHORITY_MATRIX.md` (APEX-SOURCE-001). File presence alone does not establish runtime, deployment, registry, execution, or certification authority.

</details>


## OMEGA-G0-ADMISSION-001 — continuous admission and configuration separation

The owner-approved [operational admission and configuration context amendment](docs/canon/OMEGA_G0_ADMISSION_CONFIG_CONTEXTS_20261117.md) governs recurring provider admission. Twenty-five observations remain a separate commissioning witness; they are not a per-provider-selection or per-cycle startup prerequisite. Build/test, commissioning and operational mainnet configuration are separate contexts. Real Polygon reads remain SHADOW-only without separate LIVE authorization.
