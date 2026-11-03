# Weapon visual replacements

Scorpion Evo, Kar98k and P90 now use authored imported assets. The MP7's existing prototype is deliberately preserved because the downloaded alternative failed visual quality review. The Lynx cat and meowing audio are not rebuilt by this upgrade.

| Weapon | Visual | Source | State |
|---|---|---|---|
| Scorpion Evo | Textured scorpion | Guillaume "GuieA_7" Englert / CC BY-SA 4.0 | Installed and file-verified; in-game untested |
| Kar98k | Fishing rod and reel | Justin Randall / CC BY 3.0 | Installed and file-verified; in-game untested |
| P90 | Textured toaster | MilkAndBanana / CC0 | Installed and file-verified; in-game untested |
| MP7 | Existing nailgun prototype | Original MWC procedural asset | Preserved; proper authored upgrade pending |

![Scorpion software preview](../assets/authored-weapons/scorpion/preview/preview.png)
![Fishing rod software preview](../assets/authored-weapons/fishing_rod/preview/preview.png)
![Toaster software preview](../assets/authored-weapons/toaster/preview/preview.png)

These are software previews, not game captures. Read the [expansion report](expansion.md) for source links, tests and remaining work, and [asset attribution](../assets/authored-weapons/ATTRIBUTION.md) for licenses.

Each accepted model keeps its original geometry, UVs and material colors through a checked atlas and uniform coordinate fit. `weapon_models/imported.py` verifies asset hashes; `weapon_models/bundles.py` adds visual mesh/material/texture objects and masks only the owning weapon's original renderers. Optics/aim transforms, original materials, animations, scripts, collision and weapon statistics are not replaced. Source mesh sizes above the existing uint16 writer's limit fail explicitly.

The manager cards install independently. `config/weapon-asset-selections.json` makes the retained MP7 source explicit. Legacy procedural exports remain available for old manifest verification and rollback; missing imported assets never silently trigger procedural generation.

For standalone development, configure a local game preset, record the baseline with `weapon_models_cli.py prepare`, then `build`, `verify`, and `install`. Do not install a standalone old stage over other selected mods: use the manager's composition and transaction engine. `restore` returns a standalone layer to its recorded preceding baseline and refuses unknown hashes. It never closes a running game.
