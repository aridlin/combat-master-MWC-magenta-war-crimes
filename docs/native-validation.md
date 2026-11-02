# Historical procedural-cat validation — November 2, 2026

This records the earlier gray procedural prototype. It predates the M1A0
full-tail import, sight, helicopter and cat-audio modules. Consult
[verification.json](verification.json) for the current installed/tested state.

Steam build 24397779, Unity 6000.3.19f1, native Linux IL2CPP, KDE Wayland,
RTX 4060 Ti. The game ran windowed at 1920×1080 for inspection, using its
native OpenGL renderer. This is not a native-4K performance test.

The process ran in a separate network namespace with only loopback and no
routing table. The interface counters remained zero. Steam initialization
could not create its account pipe, so the normal game UI used an isolated
guest profile. Account data and weapon unlocks were not edited. Menu input
used ordinary desktop keyboard/mouse events; no game-process injection or
memory inspection was used.

## Lynx results

- v1: Cat rendered, but stood perpendicular to the gun. Receiver and magazine
  remained visible. A file-only mesh/reference check had not detected this.
- v2: Disabling every Lynx-specific visual renderer, including initially
  meshless skinned renderers, removed the original receiver and magazine.
  The cat was horizontal but faced the stock.
- v3: Cat is upright and faces forward in the actual weapon showcase.
  Original receiver and magazine remain hidden. Shared optic is retained.
  The palette, body, legs, ears, tail and whiskers render.

The final quaternion maps cat mesh +Y forward to weapon +Z forward, and
cat mesh +Z up to weapon +Y up. Both visual roots receive the same transform.
Existing weapon transforms, bones, animations, scripts, audio and collision
objects retain their original data. The model is rigid, with no cat rig.

The guest profile permits showcase previews but locks equipping the Lynx.
Therefore firing, muzzle/mouth alignment, reload, ADS clearance, first-person
placement, third-person placement and LOD transitions remain unverified.
The screenshot is preview evidence, not evidence for these behaviors.

## Blue loot crates

Box-1, Box-2 and Box-3 materials in src/src use dedicated bright-blue albedo
copies (#008CFF). The installed file matches the verified output. All other
original objects are byte-exact except the selected albedo material pointers.
Alpha is verified unchanged. The CombatZone world appearance is untested.

## Other observations and limits

An offline Cargo HD bot match loaded with magenta arms and orange weapons.
Some map surfaces rendered solid magenta. The native log reports an unsupported
Hidden/Universal Render Pipeline/DBufferClear shader. The cause of the map
appearance was not isolated and must not be attributed solely to this warning
or either new module. No controlled original-bundle comparison was performed.
No FPS/performance improvement is claimed.

The test game was closed and the pre-test Unity preferences were restored
byte-for-byte. The approved v3 cat and blue crate bundles remain installed.
Two earlier cat versions were restored to the halftone baseline before each
replacement; both restoration operations completed and verified their hashes.

## Remaining acceptance checks

1. Use an already unlocked Lynx in an offline or authorized environment.
2. Check first-person holding, ADS, firing and muzzle position, and reload.
3. Inspect third-person orientation and all relevant attachment/LOD variants.
4. Inspect all three loot-crate variants inside CombatZone, including opening.
5. Compare original and modified map rendering under the same renderer.
6. Measure frame times at 3840×2160 using identical settings and workload.

## Restoration

Run from the configured checkout. Restore each optional module first:

```sh
.venv/bin/python catgun_cli.py restore
.venv/bin/python crate_colors.py restore
.venv/bin/python deploy_halftone.py restore
```

The first two restore the full halftone baseline for their affected bundles.
The last restores the preinstall state saved by halftone deployment. These
commands close the identified game process and reject unknown installed
hashes. They do not remove backups or staged builds.
