# Weapon visual replacements

Scorpion Evo, Kar98k and P90 now use authored imported assets. The MP7 now uses Liberi Arcano's proper authored Poons power nailer, replacing its earlier procedural placeholder. The Lynx cat and meowing audio are not rebuilt by this upgrade.

| Weapon | Visual | Source | State |
|---|---|---|---|
| Scorpion Evo | Textured scorpion | Guillaume "GuieA_7" Englert / CC BY-SA 4.0 | Native offline armory rendering verified; ADS/reload/LODs pending |
| Kar98k | Fishing rod and reel | Justin Randall / CC BY 3.0 | Native offline armory rendering verified; ADS/reload/LODs pending |
| P90 | Textured toaster | MilkAndBanana / CC0 | Native offline armory rendering verified; ADS/reload/LODs pending |
| MP7 | Poons power nailer | Liberi Arcano / CC BY 4.0 | Native offline armory/showcase rendering verified; ADS/reload/LODs pending |
| Minigun | Actual TF2 Medigun | User-owned local TF2 installation; no Valve data bundled | Installed/file-verified; native artwork rendering checked through a private MP.V visual alias; actual Minigun pose/world appearance untested |

![Scorpion software preview](../assets/authored-weapons/scorpion/preview/preview.png)
![Fishing rod software preview](../assets/authored-weapons/fishing_rod/preview/preview.png)
![Toaster software preview](../assets/authored-weapons/toaster/preview/preview.png)

These are software previews, not game captures. Read the [expansion report](expansion.md) for source links, tests and remaining work, and [asset attribution](../assets/authored-weapons/ATTRIBUTION.md) for licenses.

Each accepted model keeps its original geometry, UVs and material colors through a checked atlas and uniform coordinate fit. `weapon_models/imported.py` verifies asset hashes; `weapon_models/bundles.py` adds visual mesh/material/texture objects and masks only the owning weapon's original renderers. Optics/aim transforms, original materials, animations, scripts, collision and weapon statistics are not replaced. Source mesh sizes above the existing uint16 writer's limit fail explicitly.

The manager cards install independently. `config/weapon-asset-selections.json` makes the retained MP7 source explicit. Legacy procedural exports remain available for old manifest verification and rollback; missing imported assets never silently trigger procedural generation.

For standalone development, configure a local game preset, record the baseline with `weapon_models_cli.py prepare`, then `build`, `verify`, and `install`. Do not install a standalone old stage over other selected mods: use the manager's composition and transaction engine. `restore` returns a standalone layer to its recorded preceding baseline and refuses unknown hashes. It never closes a running game.

November 3 native menu checks confirmed all four authored replacements render, and the existing M1A0 Lynx cat retains its rear body and full tail. The P90 showcase camera mostly sees the toaster's plain side, so this is limited appearance evidence. Source geometry and gold native attachments remain separate. Raised/rolled placement still needs first-person inspection. See [actual capture gallery](screenshots/README.md).

## Medigun artwork control, November 6

![Existing Medigun artwork in the native renderer, private MP.V alias only](screenshots/medigun-native-art-alias-nov6.png)

A private cosmetic alias attached the **existing installed** Medigun mesh and
material to MP5 visual roots in the copied offline profile. The native game
renders its red body, dark barrel and handle; original MP.V gold parts remain
visible. This checks artwork loading/shading, not the Minigun's actual pose,
grip, animations, world view or ADS clearance. The alias was never installed.
No Minigun equip/unlock, damage, collision, animation, audio or script change was
made. Both intended installed Minigun visual branches already have their Medigun
replacement child; the file audit found no missing branch. The Kill Chains menu
itself still uses a static picture.

[Evidence and hashes](medigun-native-art-verification.json) record the limited
scope. The native game exited 0 and the host profile stayed exact; Gamescope
teardown returned 139. A separate [original-arm ADS control](native-pose-controls.md)
now establishes a bounded pose-inspection path for subsequent model checks.

## Official Kar preview and held-view limit, November 6

![Installed fishing rod in the official Kar98K showcase](screenshots/fishing-rod-official-preview-nov6.png)

The installed rod and native scope render through the game's own Preview button.
The isolated guest retains the Kar98K Level 17 lock; the observed Preview screen
is a rotating showcase with no range control. A separate unchanged copy of the
current local profile still opens as a level-1 guest in this network-isolated
setup. No authenticated owned-weapon session was established and progression
was not edited.

This adds native showcase evidence, not held/ADS alignment acceptance. The rod's
reel clearance and the nailer/toaster sight support remain pending a permitted
owned-weapon range test. [Captures and exact limits](weapon-preview-limits-verification.json)
record both native exits and unchanged host profiles.
