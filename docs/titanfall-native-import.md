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

Remaining work includes a supported local-import workflow on Linux/Windows,
material-preserving mesh packing, native world/first-person bundle checks,
independent installer options/previews, magenta defaults, and offline animation,
arm-volume and helicopter-introduction review. Existing Stim remains available;
Dozer/Shrek and Lynx/audio are preserved.

Format references: [Northstar MDL documentation](https://docs.northstar.tf/Modding/guides/tools/MDLModding/),
[tf2vpk MIT source](https://github.com/pg9182/tf2vpk), and
[RSX format definitions](https://github.com/r-ex/rsx/tree/18cd364421c883d475a78643e3796caf19204355/src/game/rtech/utils/studio).
Only binary layout facts were used for the original Python MDL implementation;
RSX exporter code is not included in it.
