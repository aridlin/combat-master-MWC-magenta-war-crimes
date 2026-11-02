# Combat Master MWC (Magenta War Crimes)

Native Linux visual-asset experiments for **Combat Master**: deterministic
halftone retextures and an experimental Lynx cat gun.

![MWC gameplay: magenta arms, orange weapon and simplified world surfaces](docs/screenshots/ship-deck.jpg)

The screenshot comes from user-recorded gameplay. It demonstrates the
retexture work, not the cat prototype. More captures are in
[the screenshot gallery](docs/screenshots/README.md).

## Current state

| Feature | State |
| --- | --- |
| Fine / Quiet Light-Dot Halftone | Implemented and applied locally; gameplay captures available |
| Shared albedo separation | Implemented with category-specific copies and verified material bindings |
| Map texture arrays | Implemented for the four inspected BC7 albedo arrays, 50 layers |
| Lynx cat geometry | Original mesh exported as OBJ and self-contained GLB |
| Lynx bundle prototype | Installed locally; cat rendered in offline armory and showcase preview |
| Cat orientation and original receiver/magazine hiding | Verified in offline showcase after two visual corrections |
| Cat firing, reload, ADS and muzzle alignment | **Not verified**; isolated guest profile has the weapon locked |
| Bright blue CombatZone loot crates | Three materials installed and file-verified; world appearance not yet tested |
| FOV management / crosshair overlay | Not implemented in this repository |

The inspected build is Steam **2281730**, build **24397779**, native Linux
Unity **6000.3.19f1 / IL2CPP**. Unknown builds stop at the version/hash guards.
There is no Mono loader, process injection, network modification or integrity
bypass. Use these experiments offline or in an explicitly authorized setup.

## Setup

Use Python 3.12, a native Linux Steam installation, and enough space for
original snapshots and staged bundles. The tools do not distribute game data.

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python configure.py
.venv/bin/python -m unittest discover -s tests -v
```

`configure.py` finds Steam libraries and creates an ignored `halftone.json`.
If several installs exist, select one with `--library /path/to/SteamLibrary`.
To build from an existing original snapshot rather than an already modded
installation, add `--original-bundles /path/to/original/bundle/tree`.

## Halftone workflow

```sh
.venv/bin/python halftone_cli.py generate-textures
.venv/bin/python halftone_cli.py scan-assets
.venv/bin/python halftone_cli.py classify-assets
.venv/bin/python halftone_cli.py apply-textures --dry-run
.venv/bin/python halftone_cli.py apply-textures
.venv/bin/python halftone_cli.py apply-array-textures
.venv/bin/python halftone_cli.py separate-shared-albedos
.venv/bin/python halftone_cli.py verify-bundles
```

Review the classification and staged output before installing:

```sh
.venv/bin/python deploy_halftone.py install --dry-run
.venv/bin/python deploy_halftone.py install
# Restore the exact preinstall state:
.venv/bin/python deploy_halftone.py restore
```

Installation closes the identified game process, snapshots the installed
files, replaces verified bundles, and records hashes in a deployment journal.
It does not launch the game. Unknown installed hashes are rejected. The cat
prototype and blue crate module must be restored before replacing the underlying halftone stack.

## Exact visual preset

![Exact source texture: characters](assets/halftone/characters.png)

Eight canonical RGB images use a 512×512 tile, regular square lattice,
32-pixel pitch, integer radius 3, and `np.rint(base + (255-base)*0.18)` dot
colors. Dots occupy exactly **2.83203125%** of the source. There is no noise,
Bayer matrix, source-luminance modulation, emission or baked lighting.

| Category | Base sRGB |
| --- | --- |
| Characters, arms and equipment | `#FF00FF` |
| Weapons and attachments | `#FF8500` |
| Vegetation | `#439B45` |
| Sheet metal | `#87939B` |
| Concrete | `#B5ADA0` |
| Wood | `#98663D` |
| Dirt/gravel | `#796B50` |
| Glass | `#65C9D6` |

Unknown props use an explicit neutral concrete fallback in the full-surface
preset. Mixed atlases/layers receive documented whole-surface approximations;
the tool does not infer semantic regions inside an atlas. UI, effects,
normals, masks, packed material maps and baked lighting remain separate.

The local full pass changed 5,234 albedos, added 11 category copies for six
shared sources, and changed 50 map-array layers across 76 bundles. These are
results for the inspected build, not portable fixed counts or universal
coverage guarantees for later builds/runtime downloads.

Original UVs and material tiling determine physical scale. The requested
1.28-meter tile is **not** a measured world-space result. Compression,
filtering and lighting introduce colors beyond the two exact source RGBs.
RGBA array conversion preserves every decoded alpha mip but adds about
176 MiB of texture storage. Frame-time/VRAM behavior has not been measured.

## Experimental Lynx cat

![Original procedural cat mesh preview, not an in-game screenshot](assets/cat/preview.png)

The original cat has **3,690 vertices and 7,106 triangles**. It is attached
as a separate rigid visual child to both inspected Lynx roots. Dedicated
empty render-mesh copies replace 111 Lynx-specific render bindings, and all
Lynx-specific renderers are disabled, including initially empty renderers
that the game populates at runtime. The original
meshes remain available to collision and other references. Shared optics
remain. Existing weapon bones, transforms, animations, sounds, scripts and
muzzle nodes keep their original data.

```sh
.venv/bin/python catgun_cli.py model
.venv/bin/python catgun_cli.py build
.venv/bin/python catgun_cli.py verify
# Explicitly opt into the offline prototype:
.venv/bin/python catgun_cli.py install --dry-run
.venv/bin/python catgun_cli.py install
.venv/bin/python catgun_cli.py restore
```

`catgun.json` controls position, quaternion rotation (x, y, z, w), and scale. Use a fresh output/backup directory
for a new variant. File-level verification checks the new vertex/normal/UV/
index data after reopening, all new local asset references, exact original
object bytes, and the narrow set of permitted visual changes.

The cat now renders in the actual native Linux armory and showcase preview.
The first test caught a perpendicular cat and visible receiver/magazine;
subsequent builds corrected orientation and disabled runtime-populated visual
renderers. The shared scope intentionally remains.

![Actual offline Lynx showcase screenshot](docs/screenshots/lynx-cat-showcase.png)

**This remains a prototype.** Firing, reload, mouth/muzzle alignment,
scope/ADS clearance, first/third-person behavior and LOD transitions are
unverified. The network-isolated guest profile could preview the Lynx but
could not equip it because it is locked. No unlock/profile edits were made.
See [the native test record](docs/native-validation.md).

## Bright blue CombatZone crates

`crate-colors.json` selects bright blue `#008CFF` with the existing quiet dots.
The module gives the three `Box-1`, `Box-2`, and `Box-3` MilitaryCrate loot
materials dedicated albedo copies. Other users of the old textures retain
their existing colors. Alpha, normal maps, lighting, geometry, interaction
and loot data remain unchanged. Generic decorative boxes and store crates
are outside this selection.

Build the full halftone baseline first, then:

```sh
.venv/bin/python crate_colors.py build
.venv/bin/python crate_colors.py verify
.venv/bin/python crate_colors.py install --dry-run
.venv/bin/python crate_colors.py install
.venv/bin/python crate_colors.py restore
```

The three materials are installed and hash-verified locally. Their actual
appearance in the CombatZone map has not been visually tested. Restore both
crate and cat modules before restoring the underlying halftone installation.

## Layout

```text
halftone/              generation, asset scan, classification, encoding, verification
catgun/                original geometry, Unity mesh serialization, reversible deployment
assets/cat/            original OBJ, GLB, palette and clearly labeled previews
config/                portable palette/rules and inspected array-layer mapping
tests/                 deterministic pattern, classification, alpha, material and mesh tests
docs/screenshots/      curated stills from user-provided gameplay recordings
```

Game bundles, original backups, account-specific configuration, raw clips and
local scan reports are ignored. The MIT license covers original code and
procedural assets; the game and captured game content retain their own owners.
