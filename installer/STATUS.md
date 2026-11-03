# Expansion preview status — 2026-11-03

The expansion report in docs/expansion.md is the current feature matrix. Three authored weapon upgrades and the independently selectable sky module passed bundle verification. Existing Lynx model/audio, MP7 objects, operator texture bundles and original weapon materials remain byte-exact.

Forty-three automated tests collected: 42 passed and one existing data-dependent test skipped. Native skinned-mesh codec roundtrip passed on a copy of a 741-vertex/83-bone mesh; no new character rig was installed. Character models remain blocked on authenticated downloads, asset suitability/permissions and target/rigging work.

The local legacy manager state was initialized only after validating known installed stage hashes and verifying 81 original/installed bundle entries. Expansion rollback to the precise previous mod stack and reinstallation were exercised. Final sky cloud layout was revised after visual review; the current final build is recorded in the private workspace deployment report. Original-scene deterministic halftone menu supersedes the rejected AI redraw.

Linux and Windows frontends compile. Portable packages include updated thumbnails, source/license records and runtime data. Linux packaged diagnostics are checked separately from source tests. Windows expanded package runtime/game compatibility remains unverified; do not label cross-compilation a Windows runtime test.

No new expansion feature has yet passed in-game acceptance. ADS/reload/LOD, sky HDR/exposure, animation and helicopter checks remain required. The test VM stays paused; no game is closed automatically.
