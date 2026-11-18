# Bor 2.11.1 source-lock reconciliation

The host repair reports Bor 2.11.1, Git commit `156755608234bb4220460abd4d8c9ef691691010`. The previous source release lock still selected 2.11.0. The release lock now selects official 2.11.1 amd64 binary and mainnet sentry-configuration artifacts, using digests published by 0xPolygon's GitHub release API and rechecked November 17, 2026 Pacific.

Binary package SHA-256: `8de72a68f3e9d0fb038752e2e3d89395d8d7d5ecd75aebc7915d6de0fddab404`. Configuration package SHA-256: `747f7f542739634110ed38425d918e50ffb078fe5d43cc969ed57e194114aeda`.

Authority: https://github.com/0xPolygon/bor/releases/tag/v2.11.1 (published November 13, 2026 UTC). Heimdall remains pinned to its existing 0.13.2 artifacts.

This corrects future staging provenance. It does not assert that the host configuration package was upgraded, install a package, restart a service, replace a database, or certify current canonical chain state. `stage-signed-releases.yml` still only stages hash-verified artifacts and does not install/start them. Preserve the repaired host's reviewed configuration and binary rollback evidence until a separately verified host promotion.

The latest read-only probe found a 10,192-block lag and unavailable guarded gateway; private-node runtime readiness remains OPEN. A five-second resource sample showed 26.41% aggregate non-idle CPU, including 4.04% I/O wait, and is insufficient to establish sustained saturation or justify resource changes.
