# Authored weapon assets

These models are imported from existing authored assets. They are **not** covered by the MWC code license. Keep the individual license and provenance records with redistributed derivatives.

| Replacement | Asset and author | Source | License |
|---|---|---|---|
| Scorpion Evo | Scorpion (3D), Guillaume "GuieA_7" Englert | https://opengameart.org/content/scorpion-3d | CC BY-SA 4.0 |
| Kar98k | Fishing rod, Justin Randall | https://poly.pizza/m/9gXWYDqB6vt | CC BY 3.0 |
| P90 | Toaster, MilkAndBanana | https://poly.pizza/m/5mEcP28FcV | CC0 1.0 |

Adaptations: evaluated source mesh export, triangulated corner normals/UVs, uniform scale/rotation/translation to weapon coordinates, material texture atlases with border extrusion and repeat handling, Unity visual asset serialization, and previews. No substitute primitive mesh was created. Original source object names, mesh/albedo hashes, transformation and triangle counts are recorded in each `provenance.json`.

The scorpion mesh/texture derivative remains under CC BY-SA 4.0; the attribution and license must travel with that derivative. Other game content and the separate MWC source code are not being relicensed. Legal-code copies are in `licenses/`.

A simpler Kenney CC0 toaster candidate was rejected after visual review and is not distributed as the active model. The accepted toaster is MilkAndBanana's textured model listed above.

The Lynx model and its meowing audio are not part of this upgrade. They retain their existing assets and credits.

MP7 upgrade: the downloaded HippoDevelopment nailgun was rejected at visual review and is not distributed as an upgrade. The existing MP7 prototype remains explicitly selected in config/weapon-asset-selections.json.
