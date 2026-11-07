# OMEGA Polygon node target — T-POL-137-20261106-02

Owner request: build and deploy the complete node from the selected
`House-Of-Drip-Online/POL-mainnet-full-node` repository. The owner subsequently
explicitly authorized deployments using the currently connected AWS root
identity. This supersedes the earlier non-root launch blocker for this release;
root use must remain explicit in deployment evidence and in the CLI flag.

1. One non-validator Polygon PoS mainnet node: Bor 2.11.0 and Heimdall-v2 0.13.2,
   current official AMD64 binaries, exact package SHA256s and mainnet genesis.
2. Dedicated Ubuntu 24.04 host, encrypted retained data EBS, IMDSv2, SSM
   administration, no public SSH, public P2P and private read RPC only.
3. Independent node repository/release identity. No application keys or
   inherited Asset Hunter, APEX, SYMEN, or Sovereign execution authority.
4. Install and restart safely. Refuse disk replacement, chain-data erasure,
   conflicting mounts, unreviewed CloudFormation replacements, and package
   drift. Daily crash-consistent snapshots with two recovery points.
5. Heimdall must be fresh and caught up before Bor starts. RPC readiness requires
   both chains to be healthy, Bor peers, fresh canonical headers and bounded
   height disagreement with an independent provider. Failure removes readiness.
6. Bounded HTTP and WebSocket gateway, all batch members checked, read methods
   only, restricted log ranges, and forced reconnect on loss of readiness.
7. Structured health, disk metrics, CloudWatch alarms and source-bound evidence.
8. Completion requires real host/service, synchronization, canonical state,
   HTTP/WSS, restart and consumer-path observations. Passing source tests,
   native binary smoke, or CREATE_COMPLETE alone never certifies this target.
9. Historical capability is explicit. A pruned full node does not promise
   archive state or a complete historical event census. Keep independent
   historical-capable providers for unsupported ranges until measured otherwise.

Performance is measured after synchronization. No latency or hydration
improvement is claimed from installation alone. Initial synchronization can
outlast the provisioning operation; report its actual progress rather than
declaring a healthy head in advance.
