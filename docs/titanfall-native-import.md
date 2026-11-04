# Native Titanfall 2 pilot import work

The requested successor to the Stim default is the armored **human Grapple
pilot**, with a **female Pulse Blade** option kept separate. The installed
assignment has not changed while this importer is under development.

A local Titanfall 2 installation supplies the real geometry, rigs and original
textures. No Respawn/EA model, texture, RPak, Starpak or VPK is bundled in this
repository. Local access grants no redistribution license.

Implemented source support:

- Read-only VPK 2.3 indexing, bounded chunk reads, decompressor callback and
  whole-asset CRC verification. Valve VPK parsing remains separate.
- Embedded MDL53 VTX/VVD extraction, with range, overlap, length and checksum
  checks. LOD0 geometry, material references and authored skin weights only.
- Distinct MDL53 strip/group and bone/material layouts; unsupported quad
  topology fails explicitly rather than being treated as a triangle strip.
- Bounded base RPak7 visual indexing and original BC1/BC3/BC7 mip decoding,
  including explicit Starpak directory/range checks and material ambiguity errors.
- A local importer packs both pilots into the existing source format, retaining
  every authored vertex and triangle while using the existing 512px atlas tiles.
  Both real pilots together occupy about 4.6 MiB as packed sources, rather than
  keeping gigabytes of intermediate color arrays.
- Explicit correspondence from the native Titanfall humanoid rig to Combat
  Master's rig, including fingers and anatomical helper ancestry.

Local checks recovered the Grapple male (`pilot_medium_geist_m`, 25,847 vertices,
33,048 triangles) and female Pulse Blade (`pilot_medium_reaper_f`, 23,760 vertices,
32,777 triangles). Both pass initial Ranger rest-pose fitting. Private CPU
renders show both complete designs with their original colors and equipment.
These are reference renders, **not evidence of in-game animation acceptance**.

Texture research additionally decoded the local base RPak, verified its complete
page extents, resolved the pilot materials' albedo GUIDs and extracted original
full-resolution streamed mip data. The RPak reader and compact local import API are included in source. The
separately licensed source-built decoder remains a private development tool;
its public installer integration has not been completed. The standalone decoder ran in a
network-isolated read-only sandbox and was not linked into the MIT installer.

## Prepared-source import in the manager

The Operators tab now has two distinct choices: **Titanfall Grapple pilot** and
**Titanfall female Pulse Blade**. Both default to magenta, independently of the
legacy Stim option. Neither is assigned to an operator automatically.

Enter the parent folder containing `titanfall_grapple/` and
`titanfall_pulseblade_female/`, then choose **Import prepared pilots**. Each
prepared model contains exactly `source.json`, `source.npz` and `albedo.png`,
as produced by `model_import.titanfall2.import_models`. The manager verifies
identity, hashes, bounded arrays, bone correspondence and weights before copying
sources into its private `operator-imports` directory. It creates local thumbnails
and retains replaced source revisions under `operator-imports/history`.

Importing does not install bundles or change operator assignments, color choices
or enabled mods. Choose the operator slot, Magenta setting and matching arms,
then Apply to compose those choices with the other enabled mods. Shared-prefab
conflicts fail explicitly. A frontend that omits models already used in saved
assignments or appearance preferences is rejected by the current backend.

This is a **prepared-source** workflow. Automatic import directly from a Steam
Titanfall 2 folder is not yet included in the portable installer; the reviewed
local decompression tools are still separate development inputs. Windows GUI
runtime validation of this new import control remains pending.

## Checks completed on 2026-11-04

Both pilots passed world and first-person bundle serialization, reference and
unchanged-object checks. The private world build retained 34,566 unrelated
objects byte-for-byte; first-person retained 144,986. These builds change owned
visual renderer mesh/material/bounds fields while preserving the native rig,
animations and gameplay components.

The native Linux game rendered the Grapple on Ranger and the female Pulse Blade
on a private Rush test slot, including recognizable front and back armor and
weapon-holding idle poses. The private session also rendered the new magenta
pilot arms in stationary first person. This was a network-isolated 1280x720,
30-FPS-capped test; it is not a performance benchmark. Full running, jumping,
sliding, aiming, reload and helicopter-introduction acceptance remains pending.
The game exited with code 0; Gamescope exited with 139 during shutdown. The host
profile and installed operator assignments were unchanged. In particular, the
female pilot has not been assigned to the user's Rush slot.

Existing Stim remains selectable. Dozer/Shrek and Lynx/audio are preserved.
The development test suite completed 130 tests: 129 passed and one existing
data-dependent test skipped.

Format references: [Northstar MDL documentation](https://docs.northstar.tf/Modding/guides/tools/MDLModding/),
[tf2vpk MIT source](https://github.com/pg9182/tf2vpk), and
[RSX format definitions](https://github.com/r-ex/rsx/tree/18cd364421c883d475a78643e3796caf19204355/src/game/rtech/utils/studio).
Only binary layout facts were used for the original Python MDL implementation;
RSX exporter code is not included in it.
