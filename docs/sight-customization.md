# Offline sight customization

The inspected English localization identifies Steg Spikes as scope 33,
Dino_Ironsight. The reticle item GUIDs were resolved through the game's asset
catalog and bundle containers. The map covers 48 named reticle items across
root/root, src/weapons/weapons, and src/weapons/attachments.

The module replaces 38 reticle pictures with the existing Sun pixels. Reflex
and sniper variants use reflex Sun (264); ACOG variants use ACOG Sun (518).
Red Dot, Red Arrow, Toxic Tris, Blue Dot, Circle Dot, Sun and Pulse remain
byte-exact, including duplicated names in different families. Semi-Circle Dot
is a different named item and is replaced. Item names and unlocks do not change.

Steg Spikes gets a simple rear notch and front post instead of the tall
prehistoric mesh. The three LOD filters point at a dedicated new visual mesh;
original mesh objects remain intact. Its old luminous dots are hidden. Existing
AimPoint, transforms, attachment data, zoom, scripts, animations and collision
remain byte-exact. The new front-post top is aligned to the inspected AimPoint
height (0.0147 m); game-visible ADS alignment is not yet verified.

Use only offline or explicitly authorized environments. This is an asset
replacement, not a modding API supplied by the developer. No process injection
or integrity bypass is used.

```sh
# Record the intended current installed baseline; game files are read only.
.venv/bin/python sight_customization.py prepare
.venv/bin/python sight_customization.py build
.venv/bin/python sight_customization.py verify
.venv/bin/python sight_customization.py install --dry-run
.venv/bin/python sight_customization.py install
.venv/bin/python sight_customization.py restore
```

Use fresh output/backup paths for another variant. Prepare records hashes, not
permission to overwrite future unknown files. Every build/deployment checks
those hashes and the game build. Serialization is reopened and checked; Sun
pixels match exactly, protected reticles and unrelated original objects remain
byte-exact, and the new iron-sight geometry round-trips exactly.

## Layered rollback

Sights are built on the current installed cat/halftone stack. Restore them first:

```sh
.venv/bin/python sight_customization.py restore
.venv/bin/python catgun_cli.py restore --config catgun.local.json
.venv/bin/python crate_colors.py restore
.venv/bin/python deploy_halftone.py restore
```

Use the cat configuration actually installed. Unknown hashes stop restoration
rather than overwriting another variant. Keep all backups and manifests.

## Testing still required

- Check Steg Spikes appearance and alignment in real hipfire and ADS.
- Check front/rear post visibility on compatible weapons and all LODs.
- Preview each changed reticle and compare with Sun in the same optic.
- Confirm every exception still has its original picture.
- Check sniper Sun at its original zoom and render scale.

Local bundles are installed and file-verified. These sight changes have not
been visually validated in-game; no accuracy or performance claims are made.
