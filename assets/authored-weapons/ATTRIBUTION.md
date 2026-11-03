# Authored weapon assets

These models are imported from existing authored assets. They are **not** covered by the MWC code license. Keep the individual license and provenance records with redistributed derivatives.

| Replacement | Asset and author | Source | License |
|---|---|---|---|
| Scorpion Evo | Scorpion (3D), Guillaume "GuieA_7" Englert | https://opengameart.org/content/scorpion-3d | CC BY-SA 4.0 |
| Kar98k | Fishing rod, Justin Randall | https://poly.pizza/m/9gXWYDqB6vt | CC BY 3.0 |
| P90 | Toaster, MilkAndBanana | https://poly.pizza/m/5mEcP28FcV | CC0 1.0 |
| Impact grenade | Sonic Ball Spin / Sonic Dash, Swenzy | https://sketchfab.com/3d-models/sonic-ball-spin-sonic-dash-obj-blend-c99e3050331c442bad73028571acb51e | CC BY 4.0 |

Adaptations: evaluated source mesh export, triangulated corner normals/UVs, uniform scale/rotation/translation to weapon coordinates, material texture atlases with border extrusion and repeat handling, Unity visual asset serialization, and previews. No substitute primitive mesh was created. Original source object names, mesh/albedo hashes, transformation and triangle counts are recorded in each `provenance.json`.

The scorpion mesh/texture derivative remains under CC BY-SA 4.0; the attribution and license must travel with that derivative. Other game content and the separate MWC source code are not being relicensed. Legal-code copies are in `licenses/`.

A simpler Kenney CC0 toaster candidate was rejected after visual review and is not distributed as the active model. The accepted toaster is MilkAndBanana's textured model listed above.

The Lynx model and its meowing audio are not part of this upgrade. They retain their existing assets and credits.

Sonic: downloaded from the public Objaverse mirror of the creator's CC BY 4.0
model. Coincident vertices were welded within each authored object before
reducing 499,000 triangles to 5,979. Surface-area and source/result bounds checks
and renders were reviewed; original authored texture retained. The result is
uniformly fitted to a grenade visual. No Sonic sound recording is bundled.

An earlier HippoDevelopment nailgun candidate was rejected at visual review and
is not distributed. The active MP7 replacement is the authored Poons 460 below.

MP7 nail gun: **3December 2021 Day 3: Power Tool / Poons 460**, by **Liberi Arcano**, [original creator listing](https://sketchfab.com/3d-models/32172b0e57f74bddb401c5843c5354e4), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Downloaded from the public Objaverse mirror of the Creative Commons model. Authored geometry and markings retained; uniform fitting, rotation and color-material atlas conversion. Source SHA-256 and exact transformations are in `nail_gun/provenance.json`.
