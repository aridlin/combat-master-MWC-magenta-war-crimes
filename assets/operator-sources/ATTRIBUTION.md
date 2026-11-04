# Operator asset credits and licenses

These assets have their own licenses; the project's MIT license does not
relicense them or grant rights to the characters' trademarks. Each `source.json`
records the original download hash, converted mesh/texture hashes and changes.

| Package | Creator and original source | License | Changes |
|---|---|---|---|
| Shrek | [HarrisonHag1, Shrek HD](https://sketchfab.com/3d-models/ee9fbba7e7a841dbb817cc6cec678355) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [local text](licenses/CC-BY-4.0.txt) | Control sphere omitted; original separate eyes bound to the original head joint; material/UV atlas packed. Original outfit retained. |
| Mario | [Skelenius507, Mario (Super Mario Bros. Wonder)](https://sketchfab.com/3d-models/9d0f8b1fb8714e6c9aca8ed17266aa1e) | CC BY 4.0 | Unweighted controls omitted; original vertex-color/base-color/alpha graphs baked per object to original UVs; original mesh and skin retained. |
| Minecraft Steve | [Vincent Yanez, Steve](https://sketchfab.com/3d-models/cb228dcc137042cc9a3dc588758cc6e9) | CC BY 4.0 | Existing classic mesh/pixel skin retained; explicit block-character rig and interpolated knee/elbow surface cuts added; nearest texture sampling. |
| Titanfall Stim pilot | [Paris, Pilot Stim (Titanfall 2)](https://sketchfab.com/3d-models/pilot-stim-titanfall-2-9f42c6d4503841a7a4729c2e9f64047c) | [CC BY 4.0](licenses/CC-BY-4.0.txt) | Authored static mesh and UVs retained, albedo packed. Skin and rest-pose fitting are generated locally from the user's native operator rig; no native geometry, bind matrices or animations are packaged. |
| Fishguy body | [Andris Gauracs, bodybuilder_unity](https://github.com/andrisgauracs/bodybuilder_unity) | MIT, as declared in the exact [upstream README](licenses/Body-source-README.md); [standard reference text](licenses/MIT.txt) | Existing AI-assisted muscular model, with original human head removed; authored leg surfaces expanded/recolored as blue trousers. Original Mixamo skeleton retained as source skin. No source animations, controller or scene imported. |
| Fishguy sardine head | [Atsushi Konno / QSDN Inc., jinbei3d](https://github.com/atkonn/jinbei3d) | [Apache 2.0](licenses/Apache-2.0.txt); original [COPYING notice](licenses/Sardine-COPYING.txt) | Existing 98-vertex sardine mesh cropped to its head, fins omitted; photographic finish replaced with flat blue/silver/white materials; separate modeled eye rings; upright head attachment. Modified for MWC in November 2026. |

The original Shrek/Mario/Steve/Titanfall files were acquired from the public
[Objaverse collection](https://huggingface.co/datasets/allenai/objaverse), with
each creator's individual license checked separately. The collection's license
does not replace the individual asset licenses.

The shooting glasses are original MWC geometry inspired by the wraparound
[Wiley X Saber Advanced](https://www.wileyx.com/products/saber-advanced-309)
design, with a separate rust shield and black frame. No commercial glasses mesh,
manufacturer logo or texture was copied. Their source code uses the project MIT
license; this does not imply manufacturer endorsement.

TF2 mercenaries and the Medigun are **not shipped as model assets**. The importer
reads the user's local Steam App 440 VPK files into a private work directory.
Valve retains its rights; this project grants no redistribution license to that
content. Locally generated previews remain in the user's manager state.

Native Combat Master skeleton snapshots, original meshes, bundles and private
review exports must not be committed or included in installer distributions.

The native Titanfall 2 Grapple and female Pulse Blade importer reads the user's
local Steam App 1237970 VPK/RPak/Starpak files. Those Respawn Entertainment / EA
models, rigs and textures are **not shipped**. Local imports grant no new
redistribution rights. They are distinct from the Paris CC-BY Stim fan model
above. Import provenance records retain original model and texture mip hashes.
