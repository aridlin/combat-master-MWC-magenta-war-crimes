# Operator and model expansion — 3 November 2026

## Applied checkpoint

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
| Titanfall pilot | Proper textured source obtained. It has no skeleton; rigging is unfinished. Installer reports this limitation instead of substituting a placeholder. |
| Sonic impact grenade | Proper spin-ball source obtained, but 499,000 triangles needs reduction and review. Not installed. |
| Audiojungle / extra TF2 sounds | Correct CoopDogger Audiojungle project identified. Further source/rights review and optional audio integration remain unfinished. Existing Lynx sounds preserved. |
| Per-model magenta and separate native-operator control | Requested after this applied checkpoint; implementation in progress. |

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

**57 automated tests collected: 56 passed, one existing data-dependent test
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
