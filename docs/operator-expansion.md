# Operator and model expansion — 3 November 2026

## Applied shooting-lens correction

Shrek's rust shield now uses the game's shipped **URP Lit** shader with real
alpha blending, transparent queue, no depth write and no opaque depth/shadow
passes. The old character Custom Lit graph has fixed One/Zero blending, so its
added alpha settings could not make glass transparent. The preview exporter now
checks the actual shader instead of trusting those unsupported floats.

Only one owned MWC lens material changed; the other **34,595 character-bundle
objects** compare byte-exact. A private apply/restore returned the exact prior
bundle and choices. The correction is installed while the game was closed,
with all **81 managed installed/original bundle entries** hash-verified. Lynx
model/audio, other operators, arms and weapon transforms remain unchanged.
Close-up serialized-mesh reference renders show the eyes through the rust tint;
actual game sorting, lighting and helicopter appearance remain untested.

Two independent full character builds with different Python hash seeds now
produce the same bundle hash; newly added material properties are written in
stable order. **81 tests: 80 passed, one existing test skipped.**

## Current development checks (after v0.1.0-preview)

The released installers remain the tested v0.1.0 preview. The following source
changes are newer and have not been installed into the game or republished:

- All 14 model choices built on private copies across all 32 operator identities
  (29 unique first-person prefabs). This is a coverage sweep, not every possible
  model/slot combination. All 64 primary renderer outputs passed geometry,
  skin, material and reference checks; 144,905 other original objects remained
  byte-identical. Synthetic arm renders were reviewed for gross deformation;
  real grip, ADS and reload acceptance remain pending.
- Rush contains one empty native arm LOD. It can use a real native mesh only
  from a renderer with identical bone pointers, root bone and local frame.
  Different frames or missing donors fail explicitly; binds are never guessed.
- Optional **TF2 Medigun audio** replaces only three Minigun firing samples and
  its barrel-spin sample, importing local TF2 WAV data. PCM/FMOD roundtrips and
  exact native duration/metadata checks pass. Removing this option rebuilds the
  exact prior cat-only bundle, preserving all seven Lynx samples. No new sound
  is enabled automatically; in-game audition remains pending.

**78 tests: 77 passed, one existing data-dependent test skipped.** Both frontends and portable packages build; Linux packaged asset/module
diagnostics and virtual-display card rendering pass. The newer Windows build
still needs a runtime retest. The menu thumbnail now shows the current original-scene
halftone artwork rather than the superseded dot preview. See [the sound module](tf2-audio.md) for its source,
processing and restoration behavior.

The subsequent numerical cross-product sweep passed **812 fits**: every one of
14 source models on all 58 primary renderers in the 29 unique first-person
prefabs (covering all 32 identities). Native bind reproduction, finite bent
poses and normalized normals passed. The 14 reviewed images are representative
synthetic renders; every possible model/slot view has not been visually reviewed.

A private hand-driver candidate passed 928 numerical fits, but subsequent
[offline review using shipped clips](native-clip-review.md) exposed palm/finger
stretching. It was **rejected** and the production first-person fitter restored.
The retired probe is disabled. A separate nearest-native-hand-weight transfer
also remains private and unaccepted. Neither experiment entered a published
installer, the Audiojungle development packages or the installed game. The
baseline Fishguy grip still needs native in-game review; finite matrices and
normalized normals alone do not establish acceptable hands.

Audiojungle's original TF2 archive was inspected privately. The independent
**Audiojungle excerpts / Minigun** Extras option now reads four locally supplied
samples, rejects its overlap with vanilla TF2 Medigun audio explicitly, preserves
all seven Lynx samples, and restores the exact baseline when deselected. Native
slot timing and metadata passed actual private-bundle verification. Source audio
is not redistributed; this imports fixed excerpts rather than TF2's randomized
sound-event system. It is not installed or auditioned in-game. See the
[local importer](audiojungle-local-import.md) and [source investigation](audiojungle-research.md).

## Applied character/material correction

The three-bundle correction was **installed after the user exited**, then all
81 installed/original hashes and its three undo copies were verified. Ranger uses the actual authored **Titanfall 2 Stim pilot**, in
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
choice would silently change an unselected operator. The broader synthetic sweep is described above; all combinations still need
in-game grip testing.

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
| Earlier Ranger → Fishguy (reverted) | Replaced by the magenta Stim pilot after user feedback; Fishguy is now optional only. Earlier operator 0 prototype: Existing muscular body, loose blue trousers, actual low-poly sardine head, flat blue/silver/white finish and separate eye rings. In-game acceptance pending. |
| MP7 → authored power nailer | Applied. Proper Poons 460 model by Liberi Arcano, CC BY 4.0. Replaces the previous procedural geometry. |
| Minigun → actual TF2 Medigun | Applied from the local TF2 installation. Rigid visual follows the existing weapon root; weapon behavior is retained. In-game alignment/reload acceptance pending. |
| All nine TF2 mercenaries | Optional per-operator choices. Actual local VPK imports, native bundle and synthetic articulation tests passed; offline previews reviewed. Clothing/collar clipping and in-game animation acceptance still need work. |
| Mario | Optional choice. Authored color/alpha/vertex-color material graphs baked to original UVs; source rig adapted. Native bundle and synthetic articulation checks passed; in-game untested. |
| Minecraft Steve | Optional choice. Existing classic mesh/pixel skin; explicit rig and interpolated elbow/knee cuts added. Native bundle and synthetic articulation checks passed; in-game untested. |
| Titanfall pilot | Authored Stim pilot rigged locally, native bundle and offline deformation checks passed. Ranger correction applied and hash-verified; in-game acceptance pending. |
| Sonic impact grenade | Authored 5,979-triangle spin ball. Independent manager option; three held LOD renderers and the thrown filter/material are file-verified. Sonic+nailer then nailer-only composition preserves the nailer. Not installed; in-game untested. |
| Audiojungle / extra TF2 sounds | Separate local TF2 and Audiojungle excerpt options pass private build/removal verification with explicit shared-slot conflict handling. Neither installed or auditioned in-game. Source audio is not bundled; Lynx samples remain exact. |
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

**Earlier checkpoint:** 63 tests collected, 62 passed and one skipped. The
initial VM attempt was unavailable. The later v0.1.0 Windows GUI/backend test
passed in the Windows 11 VM, including saved model/color choices and FMOD
initialization. Windows game installation and in-game acceptance remain untested.

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

## Applied first-person size and rod-roll correction

Gameplay feedback showed excessive first-person bulk. The applied first-person
mesh correction reduces radius around unchanged native bone axes: Shrek arms
0.55/hands 0.60, Stim pilot arms 0.65/hands 0.70. It keeps joint-to-joint reach,
weights, UVs, skeletons, weapon sockets and all third-person models. Fixed-camera
serialized-mesh comparisons were reviewed. These values are editable in
`config/operator-viewmodels.json` and require rebuilding/applying the mod.

The fishing rod rolls 90 degrees around its authored shaft axis. Its child
translation compensates for the offset shaft pivot, retaining the shaft line
while moving the reel sideways out of ADS. Only the three MWC rod visual child
transforms change; native sights, meshes, animation and collision stay exact.
The editable roll/pivot is in `config/weapon-model-placements.json`.

The combined update passed private apply/restore with exact hashes restored,
then was applied after the game exited. All 81 installed/original hashes verify;
only first-person and weapon bundles changed. Third-person models, Lynx audio
and attachments remain unchanged. Latest suite: **75 tests, 74 passes,
one existing data-dependent skip**. Actual ADS clearance and slimmer-hand grip
still need in-game acceptance.

## Portable release validation

The corrected Windows frontend rendered in the user's Windows 11 VM. The
packaged backend verified all bundled model assets, and the actual Save operator
choices button preserved model assignments, independent colors and selected
mods without creating installed game state. This caught a CRLF parsing bug,
which is fixed in the shared frontend. The packaged Windows FMOD library also
initialized with sound output disabled. Actual Windows game-bundle installation
remains untested.

Public portable releases exclude the M1A0 archive: its Workshop credits identify
third-party owners, but MWC has no recorded redistribution grant. Lynx and cat
audio import a local archive instead. The user's local bundled edition retains
the requested archive. Permitted character/prop sources and license records are
included; Valve TF2 models import locally and are not redistributed.

## November 5 native TF2 first-person evidence

All nine optional TF2 arm models have now rendered in the official offline MP.V
Shooting Range using separate private Ranger arm aliases. The user's installed
Ranger remains Grapple. See [the native first-person review](tf2-first-person-review.md)
for each capture, observed defects, source limits and process results. These
stationary hipfire checks do not establish full grip, ADS, reload, movement,
helicopter or 4K performance acceptance. No game installation update was made
for this review.

Medic's matching first-person arms now use his genuine local TF2 class-specific
arm model. A native range comparison removed the previous forearm patch; the
source-installer build matches that tested private bundle byte-for-byte. His
world model and other classes' arm sources stay unchanged. Full grip/ADS/reload
acceptance remains pending; see [the detailed review](tf2-first-person-review.md#medic-actual-first-person-source-integration).
