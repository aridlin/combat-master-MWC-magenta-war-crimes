# Magenta War Crimes expansion — 2026-11-03

Three authored weapon upgrades and an independently selectable Minecraft-style sky are implemented. The Lynx cat, cat audio, existing MP7 model, operator magenta system and original weapon materials are preserved. None of the new visuals have been accepted through an in-game test yet.

| Feature | Status | Evidence / limitation |
|---|---|---|
| Scorpion Evo → authored scorpion | Built, installed, file-verified | Guillaume Englert's existing textured model, 1,544 triangles; UV/material atlas; two visual roots. ADS, reload and tail clearance untested in-game. |
| Kar98k → authored fishing rod | Built, installed, file-verified | Justin Randall's existing model, 14,860 triangles; three visual roots. Source geometry retained and uniformly fitted. In-game clipping untested. |
| P90 → authored toaster | Built, installed, file-verified | MilkAndBanana's existing textured model, 660 triangles. Kenney's simpler candidate was rejected after preview comparison. |
| MP7 → improved nailgun | Not completed; existing MP7 preserved | HippoDevelopment's downloaded model failed visual quality review. It is not installed or silently substituted. A suitable detailed construction-tool model is still required. |
| Lynx cat and meowing reload | Preserved | Named Lynx objects and the entire existing audio bundle compare byte-exact. No Lynx rebuild/import was performed for this deployment. |
| Operator magenta / custom operators | Preserved | First- and third-person operator bundles compare byte-exact with the pre-expansion installation. |
| Minecraft-style Overworld sky | Built, installed, file-verified | Seven named sky materials in five bundles; original pixel-style blue sky, square sun, block clouds. Sky-only cubemap clones; original cubemaps, scene lighting settings, geometry and environmental textures remain byte-exact. In-game HDR/exposure/face orientation and runtime lighting behavior untested. No vanilla Mojang texture files are represented as newly licensed project assets. |
| Night sky / square moon | Texture generation only | Explicit night generator exists and has tests; no night map material is currently targeted. Not claimed as an implemented night environment. |
| Dozer → Shrek | Blocked on asset access; mapping/rigging incomplete | Dozer is confirmed as operator 30 from the shipped English localization. SkangoGames' rigged Shrek is listed under CC BY 4.0, but the official download endpoint returns 401 without authentication. No Shrek archive obtained. Default operator prefab mapping and actual deformation tests remain necessary. |
| Shrek shooting glasses | Not implemented | Exact Saber Advanced model candidate by CG ARTStudio is listed for $29; no purchase made or asset obtained. No generic glasses were substituted, and fit/head-follow/helicopter visibility are untested. |
| Other defaults → Titanfall pilots | Blocked on asset access and explicit default-operator mapping | Paris' Stim Pilot and AX-7YK's authored Pulse Blade fanart are advertised under CC BY 4.0; both official archive endpoints return 401. No custom operator is targeted by a guessed name or broad regex. |
| Impact grenade → Sonic | Blocked on asset access and held/thrown target mapping | Swenzy's Sonic Ball Spin candidate is advertised downloadable under CC BY 4.0, but archive access returns 401. No ball primitive, grenade collision change or guessed impact sound was substituted. |
| Fishguy™ | Blocked on suitable body/head assets and a chosen cosmetic slot | No suitable Yujiro body plus textured sardine mesh has been obtained with verified permissions for the intended adaptation/distribution. No generic fish-headed humanoid was generated. A new server-owned inventory operator/unlock is outside this asset-only workflow; an optional visual replacement can target an existing explicitly chosen slot. |
| Mario | Blocked on asset access and slot choice | Candidate rigged model's official archive endpoint returns 401. Published uploader license/source must be checked against the actual obtained archive. No replacement installed. |
| Minecraft Steve | Blocked on asset access and slot choice | Blender3D's authored rigged Steve is advertised under CC BY 4.0; archive endpoint returns 401. No cube approximation was substituted. |

## Source assets and build tools

The exact weapon source links, authors, transformations, source object names and mesh/texture hashes are recorded under `assets/authored-weapons/`. See [attribution](../assets/authored-weapons/ATTRIBUTION.md) and the included Creative Commons license texts. The scorpion derivative remains CC BY-SA 4.0; it is not relicensed MIT.

- Scorpion: https://opengameart.org/content/scorpion-3d
- Fishing rod: https://poly.pizza/m/9gXWYDqB6vt
- Active toaster: https://poly.pizza/m/5mEcP28FcV
- Rejected nailgun candidate: https://opengameart.org/content/nailgun
- Shrek: https://sketchfab.com/models/1ed7e0ec5a4b412fb15c7ca721721eab
- Titanfall authored fanart: https://sketchfab.com/models/489986a1332d4da680036a73746eefdb
- Sonic spin ball: https://sketchfab.com/models/c99e3050331c442bad73028571acb51e
- Steve: https://sketchfab.com/models/0cffc39bdab04551bde4f8cdfbc52eca
- Mario candidate: https://sketchfab.com/models/9d0f8b1fb8714e6c9aca8ed17266aa1e
- Exact glasses candidate: https://free3d.com/3d-model/army-goggles-wiley-x-9201.html

Blender 4.5.15 LTS was downloaded from the official Blender release host and verified against its published SHA-256 (`0d2b8bb2efe97e6c8eb57de6b7322f8800e1984e3125b60decca5f6771e4773e`). Model files were opened with `--factory-startup --disable-autoexec`; asset scripts were not executed. The source conversion scripts are under `model_import/`. Transparent materials, excessive UV repetition, oversized uint16 meshes, unassigned vertices and invalid references fail rather than producing a silent approximate replacement.

Browser discovery reported that local browser access is disabled in Codex Work settings. An explicit request for signed-in Sketchfab access/direct permitted download links is pending. No login, CAPTCHA or paywall was bypassed.

## Manager integration and reversibility

The existing Scorpion, Kar98k and P90 cards now display imported-source previews and author/license descriptions. MP7 explicitly retains the existing prototype; it does not advertise a completed upgrade. The new sky card has its own switch. `config/weapon-asset-selections.json` selects authored versus explicitly preserved legacy models; an unavailable authored asset fails instead of falling back to generated geometry.

The manager composes from its original snapshots. It does not layer stale weapon output over another selected mod. Shared bundles are handled through composition; the staged updater rejects overlapping independent staged outputs that have not been composed. The local legacy installation was adopted only after its recorded hashes matched the prior stage manifests, then 81 original/installed bundle entries were verified. Private copy-on-write snapshots are used where supported; these are never mutable hard links.

`staged_bundle_update.py apply --config LOCAL_UPDATE.json` applies verified build manifests through the same locked, journaled transaction engine. `restore` with that update configuration returns to the exact recorded preceding mod stack. The manager's **Restore all originals** is the separate operation returning all managed bundles to their original snapshots. Neither operation closes a running game; both refuse live-game writes.

The user's local full-expansion rollback command is recorded in the workspace testing checklist. Deployment paths, original game bundles, private hashes/state and third-party archive downloads are not baked into the public preset.

## Validation and remaining tests

43 automated tests collected: 42 passed and one existing data-dependent test skipped in the public checkout. Tests cover imported meshes/UVs/normals, explicit legacy preservation, missing-source refusal, cubemap shared-edge sampling, celestial discs, transaction failure rollback/recovery, exclusive locking, and normalized bone-weight handling. File-level build verification reopens generated Unity bundles and compares original object bytes against a narrow visual whitelist.

The new operator skinning writer was round-tripped against a copy of an actual native 741-vertex mesh with 83 bones. Geometry, skin weights and bone indices matched after reopening; all original serialized objects stayed byte-exact. This validation copy was **not installed**. It does not establish a working Shrek/pilot/Fishguy rig, weight transfer, clothing fit or helicopter animation.

Linux's packaged backend was checked for startup/detection and asset diagnostics. Linux and Windows FT frontends compile. Windows archive generation is a packaging result; the expanded Windows GUI/backend and a Windows game installation still need runtime tests. Cross-compilation is not a Windows gameplay test.

Before claiming in-game success: inspect the three weapon models in armory, hipfire, ADS, reload and LOD views; check the square sky sun/clouds across face boundaries and map HDR/exposure; compare frame times at the same 4K settings; verify the cat/reload, MP7, gold attachments and custom operators remain visually correct. Future operator acceptance additionally requires running, jumping, sliding, aiming, weapon handling and the Warzone helicopter introduction.
