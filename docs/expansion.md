# Magenta War Crimes expansion — current status, 2026-11-06

The project now contains authored replacement meshes, per-operator assignments,
independent model color controls and recoverable bundle composition. A menu
preview or serialized mesh check is not full animation acceptance.

| Feature | Implementation and observed scope | Remaining checks |
|---|---|---|
| Scorpion, fishing rod, P90 toaster and MP7 nailer | Authored textured models integrated and installed; native offline armory/showcase checks recorded. Rod uses the requested shaft-preserving 90-degree roll and raised placement. | 4K hipfire/ADS/reload, all attachments and LODs |
| Lynx M1A0 ginger cat and audio | Preserved complete cat and original tail; native armory rear-body view checked; seven addon cat clips have exact PCM/FMOD checks. | Current first-person placement and in-game listening; the isolated guest profile has Lynx locked |
| Minigun → Medigun | Real locally imported TF2 visual integrated and installed; no Valve assets bundled. | Native first-person/world/animation acceptance |
| TF2 Medigun audio | Independent local-source option; four native Minigun slots retain durations and metadata; composition/removal/Windows PCM checks passed. | In-game listening, repetition and playback cost |
| Audiojungle | Optional local-source selector and four Minigun clip mappings implemented; private composition/restoration and Windows PCM checks pass; seven Lynx clips preserved. | Native listening/playback cost; artwork/audio is not redistributed |
| Dozer → Shrek with rust glasses | Proper existing body, separate head-attached glasses and transparent tinted lenses; matte materials and matching authored arms. Native menu reviewed. | Full animations, grip/ADS/reload and helicopter introduction |
| Armored human Grapple pilot | Real local Titanfall 2 geometry/textures, explicit bone correspondence, independent manager option and private preview. Native Ranger front/back and stationary pilot arms rendered. | Full animation/first-person/heli and performance acceptance; direct-from-Steam decoder integration |
| Female Pulse Blade | Separate locally imported option. Recognizable model front/back rendered in a private Rush test slot; not assigned to the user's Rush slot. | Same full animation/first-person/heli checks |
| Fishguy | Proper muscular body plus low-poly sardine, optional per-operator choice; native back/source skin reviewed. Native controls narrow the remaining wrist crease; experimental fixes remain rejected. | [Wrist deformation](fishguy-first-person-controls.md), grip and full movement/heli checks |
| All nine TF2 mercenaries | Real local TF2 models and private thumbnails, independently assignable. All rendered in native menus; helmet/hat, sleeve/cigarette and bandolier corrections reviewed. | Remaining grip/deformation and full animations/heli |
| Mario and Minecraft Steve | Proper authored models, optional assignments, source colors or independent Magenta; native menu appearance recorded. | Framing, grip, full animation and helicopter views |
| Sonic impact grenade | Authored curled Sonic mesh, three held LODs and thrown visual. Private composition/removal checks preserve original physics/damage components. | Native held/thrown appearance; optional Sonic audio has not been implemented |
| Minecraft-style sky | Generated mode preserved; optional local classic client importer implemented. Eight bundles/11 materials file-verified; native Parvis shows bright blue sky, square clouds and sun using the local source. | [Local importer limits](minecraft-local-sky.md): native six-sided orientation/seams, nighttime, full selection rebuild and 4K performance |
| Magenta, gold attachments, crates, menu, sights and helicopter glass | Existing independent controls and layers retained. Each module's file/reference checks are recorded. | Outstanding game-visible checks are listed in the linked feature documents |
| Mod manager | Per-operator assignment, explicit shared-prefab conflicts, per-model Magenta and separate native-operator color control, verified backups, recovery journal and restoration. New pilot import and save controls tested in the packaged Linux GUI. | Packaged GUI/runtime checks distinguish Linux from Wine; native Windows game editing remains untested |

The [v0.1.5-preview installers](https://github.com/aridlin/combat-master-MWC-magenta-war-crimes/releases/tag/v0.1.5-preview) include local classic sky import, genuine Medic viewmodel arms and optional Audiojungle excerpts. The local installation now assigns Ranger → magenta armored human Grapple and
Dozer → Shrek. Its six-bundle update was installed through the existing journaled
transaction engine; all 81 installed/original backup hashes and six undo copies
were verified. The other 75 bundles, including Lynx/weapon bundles and cat audio,
remain byte-exact. All 17 selected mods are retained. Private preview slot
assignments never become user choices automatically. The intentionally stretched
Fishguy seal is retained.

The current source suite ran **157 tests: 156 passed and one existing skip**.
Native checks used a copied profile, read-only game overrides, an isolated
network namespace and a private 1280x720 NVIDIA/Vulkan display capped at 30 FPS.
No movement or firing inputs were sent. The host profile was unchanged and the
game exited with code 0; Gamescope returned 139 during shutdown. This does not
prove broad stability or 4K performance.

## Sources and detailed evidence

- [Native operator review and material/rig corrections](operator-runtime-review.md)
- [Native Grapple and female Pulse Blade import](titanfall-native-import.md)
- [Sky binding coverage and remaining acceptance](skybox-coverage.md)
- [Weapon source attribution](../assets/authored-weapons/ATTRIBUTION.md)
- [Operator source attribution and license boundaries](../assets/operator-sources/ATTRIBUTION.md)
- [Audiojungle investigation](audiojungle-research.md) and [local TF2 audio](tf2-audio.md)
- [Testing checklist](expansion-checklist.md) and [restoration](restoration.md)

No original game bundles, EA/Respawn pilot sources, Valve models/audio or
Audiojungle archive are distributed. The public installer imports local source
data where required. The M1A0 archive is included only in the user's separate
personal edition. Third-party assets retain their source licenses.

The [initial November 3 report](expansion-2026-11-03-initial.md) is preserved as
historical evidence; its blocked/download status predates the later imports and
must not be read as the current feature state.

A full saved-selection rebuild exposed a pre-existing incomplete Lynx rotation
in the installer. The source now validates and supplies a complete native
quaternion; see [the local cat import note](m1a0-local-import.md). The failed
build stopped in private staging before installation. The previously verified
texture stage is retained for hash-checked continuation of visual modules.
