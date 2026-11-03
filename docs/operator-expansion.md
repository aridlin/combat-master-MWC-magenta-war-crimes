# Operator and model expansion — 3 November 2026

## Staged correction after gameplay feedback

The next correction is built and file-verified, **not installed while the game
is running**. Ranger uses the actual authored **Titanfall 2 Stim pilot**, in
magenta. Fishguy is an optional model choice; it is not the default replacement.
Dozer retains Shrek, his original outfit and the rust shooting glasses.

The character shader's unbound metallic texture defaulted to white. Its
metalness comes from a texture rather than the previously set scalar. Explicit
linear zero-metalness and flat-normal textures now bind to both native shader
schemas, with low body smoothness. Serialized albedo/data-map checks pass.
Fishguy's rear source render has a complete textured back; the reported gray
appearance still needs an in-game recheck after the material correction.

Renderer culling bounds now use the root bone's coordinate frame, retaining the
original animation envelope. The authored fishing rod is raised 10 cm, nailer
5.5 cm and toaster 6 cm within their visual child transforms; native sights,
weapon sockets and animations stay unchanged. Exact alignment is untested.

**Matching first-person arms** is an independent option in the Operators tab
and Extras catalogue. It extracts actual authored arm triangles, fits them to
the native arm skeleton and retains weapon IK/camera/controller data. Ranger's
pilot arms and Dozer's Shrek hands/sleeves pass serialized geometry, skin,
material and reference checks. All 32 operator identities are indexed; three
shared-prefab cases require compatible assignments and fail explicitly if a
choice would silently change an unselected operator. Other character/rig
combinations still need first-person visual and in-game grip testing.

Pilot fitting uses a private local native skin reference. Packaged sources
contain no native geometry or bind matrices. Offline reviews caught and fixed
stretched fingers and collar vertices attached to the rotating helmet.

**71 tests: 70 passed, one existing data-dependent test skipped.** The revised
three-bundle update passed apply and restore on private copies of the real
bundles, restoring exact hashes and operator assignments. Gameplay files were
unchanged by that test. In-game material, ADS/grip, animation and performance
acceptance remain pending.

## Earlier applied checkpoint

The user's pre-home update was installed through the manager's hash-guarded
transaction system. All **81 installed/original bundle entries** were verified.
A private copy of the real changed bundles passed apply → restore with exact
prior hashes and operator-assignment metadata restored.

| Feature | Status |
|---|---|
| Dozer → Shrek + rust shooting glasses | Applied to operator 30 only. Native mesh/skin/submesh/reference verification passed. Original outfit retained. In-game acceptance pending. |
| Ranger → Fishguy | Applied to operator 0. Existing muscular body, loose blue trousers, actual low-poly sardine head, flat blue/silver/white finish and separate eye rings. In-game acceptance pending. |
| MP7 → authored power nailer | Applied. Proper Poons 460 model by Liberi Arcano, CC BY 4.0. Replaces the previous procedural geometry. |
| Minigun → actual TF2 Medigun | Applied from the local TF2 installation. Rigid visual follows the existing weapon root; weapon behavior is retained. In-game alignment/reload acceptance pending. |
| All nine TF2 mercenaries | Optional per-operator choices. Actual local VPK imports, native bundle and synthetic articulation tests passed; offline previews reviewed. Clothing/collar clipping and in-game animation acceptance still need work. |
| Mario | Optional choice. Authored color/alpha/vertex-color material graphs baked to original UVs; source rig adapted. Native bundle and synthetic articulation checks passed; in-game untested. |
| Minecraft Steve | Optional choice. Existing classic mesh/pixel skin; explicit rig and interpolated elbow/knee cuts added. Native bundle and synthetic articulation checks passed; in-game untested. |
| Titanfall pilot | Authored Stim pilot rigged locally, native bundle and offline deformation checks passed. Ranger correction staged; in-game acceptance pending. |
| Sonic impact grenade | Proper authored spin ball reduced from 499,000 to 5,979 triangles with reviewed surface preservation. Impact-grenade visual targets resolved; bundle/manager integration pending. |
| Audiojungle / extra TF2 sounds | Correct CoopDogger Audiojungle project identified. Further source/rights review and optional audio integration remain unfinished. Existing Lynx sounds preserved. |
| Per-model magenta and separate native-operator control | Implemented after the applied checkpoint. Independent source-color/magenta builds and pristine native-color restoration passed bundle verification. In-game untested. |

The current Lynx cat, full tail and cat audio were preserved. The complete
`root/audio` bundle remains SHA-256
`552fa9b28d9381886672e5f9aa2fc32ff6235496baf7364a480f1061368b3053`.
The attachment bundle remains byte-identical. The only changed existing weapon
objects belong to the nailer visual or the explicitly targeted Minigun visual.
No original mesh or gameplay object was removed.

## Identity, rigging and verification

The read-only index resolves all **32 OperatorInfo records** to exact prefab
GUIDs and owned renderer IDs in build 24397779. Dozer is internally
`30.VinniePuh`, prefab `VinnePuh`; broad name matching is not used.

Native rigs share semantic bone names but use different mesh frames: some are
metres/Z-up, others centimetres/Y-up. Fitting respects each exact native bind
pose. Source VTX clockwise winding is explicitly converted before mirrored
fitting. Synthetic poses and serialized-mesh visual exports caught failures
that a successful file roundtrip alone did not reveal.

Operator builds change only owned SkinnedMeshRenderer `m_Mesh`, `m_Materials`
and `m_AABB` fields. Original skeletons, transforms, LOD groups, animation data,
scripts, collision and unrelated operators are checked byte-for-byte. New
references resolve and mesh positions/normals/UV/skin/submesh triangles roundtrip
exactly. This proves file integrity, not animation quality or gameplay visuals.

**63 automated tests collected: 62 passed, one existing data-dependent test
skipped.** Linux and Windows frontends compile. Linux packaged asset diagnostics
pass. The expanded Windows package has not yet passed current VM/runtime/game
acceptance. The VM was found aborted, and the desktop was locked during the
attempted native game UI check; no in-game success is claimed.

## Manager use

The FT installer has an **Operators** tab with an independent model dropdown
for every shipped operator. Saving choices writes a desired plan only. Applying
builds all selected mods and assignments from immutable originals before a
recoverable transaction. Shared-renderer conflicts and unavailable sources fail
explicitly. Removing an assignment restores that operator's base geometry while
respecting the selected texture mods.

TF2 models are imported read-only from a local Steam App 440 installation.
**Import TF2 previews** creates private thumbnails without changing game files.
Valve model assets are not included in distributions or the public repository.
Shrek, Fishguy, Mario and Steve have packaged, hash-verified permitted source
assets with [source/license records](../assets/operator-sources/ATTRIBUTION.md).

```sh
python -m model_import.tf2 '/path/to/Team Fortress 2/tf' '/private/work/tf2-imported'
python installer/backend.py --diagnose
python -m unittest discover -s tests -q
```

Trusted Blender conversions use `--factory-startup --disable-autoexec`. Source
scripts/controllers/animation events are never executed or imported. Private
native rig snapshots and review exports must not be redistributed.

## Rollback and acceptance

In this workspace, the pre-home transaction is recorded in
`reports/expansion/prehome-deployment.json`, with its previous mod stack and
verified undo files. Restore that exact stack with:

```sh
.venv/bin/python public-repo/staged_bundle_update.py restore --config expansion-prehome.json
```

Close the game first. **Restore all originals** in the manager restores pristine
managed bundles instead of the prior mod stack. Keep its backup directory.

Still required: real armory/helicopter appearance, running/sliding/jumping,
weapon handling, ADS/reload, LOD/culling, lens transparency, lighting and frame
performance in an offline or explicitly authorized environment. Do not infer
these results from source renders, synthetic poses or build checks.

## Independent operator colors

Each replacement model has its own Magenta checkbox. Shrek, Fishguy, Mario and Steve default to source colors; TF2 and Titanfall default to magenta. A separate checkbox controls unmodified in-game operator models. This override affects their body renderers; first-person arms follow Player textures unless the independent matching-arms option is enabled. Original native materials/albedos are cloned from verified pristine backups so shared weapon/arm textures stay unchanged. Turning native magenta on while Player textures is off is supported too. Preferences are saved separately from installed appearance metadata and committed only with a successful installation.
