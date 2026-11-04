# Skybox reference coverage

The scene-reference audit found a real gap in the v0.1.2 preview: Parvis uses
`autumn_field_4k`, not a material whose name contains “sky”. Several other scenes
also use materials outside the original target list. Selecting the sky mod in
that release therefore leaves those skies original.

Current source adds the following reviewed material bindings:

| Bundle | Material | Native layout |
|---|---|---|
| `src/maps/map_talencecm_s` | `autumn_field_4k` | Cubemap |
| `src/maps/map_museum_s` | `museum_sky` | Cubemap shared with the map library |
| `src/maps/map_electro_s` | `farmsky` | Six Texture2D images |
| `src/maps/maps` | `mossymountains` | Six Texture2D images, used by tank cleaning and tutorial scenes |

The audit follows `RenderSettings.m_SkyboxMaterial` references, rather than
assuming a material name identifies a sky. It inspected 22 RenderSettings
records across 21 scene bundles in build 24397779. Nineteen have assigned sky
materials, all now covered by the explicit target list. Three have no assigned
sky: art gallery, the original hangar and subway. The module leaves these
records unchanged; it does not add a new sky to them.

Six-image materials use Unity's documented axis labels: Front +Z, Back -Z,
Left +X, Right -X, Up +Y and Down -Y. See the [Unity 6000.3 six-sided skybox
reference](https://docs.unity.com/en-us/engine/6000.3/manual/creating-environments/sky/skybox-material-reference/shader-skybox-6sided).
The existing continuous directional generator supplies each face. The builder
rejects missing, duplicate or unreviewed texture layouts. Verification checks
the directional face and original source of every replacement binding.

Original textures are cloned, including the twelve Texture2D images needed by
the two six-sided materials. Only the reviewed sky material texture pointers
change. Original cubemaps, 2D images, RenderSettings, fog, lights, reflection
references, meshes and unrelated objects remain byte-identical. Native shader
properties, exposure, tint and rotation are retained. An existing backup can be
reused only when its hash matches the declared baseline; it is never overwritten.

## Verified scope and remaining acceptance

The private eight-bundle build passed serialization and reference checks for
11 sky materials, including both six-sided materials and twelve cloned 2D
faces. The prior seven-material manifest still passes verification. The actual
installer composition and transaction functions applied and then removed Sky
against private copies of all eight affected bundles. All original hashes were
restored, backups retained and the transaction journal cleaned.

These source changes are newer than the v0.1.2 installer binaries. They have
not been installed into the user's running game. Actual native six-sided UV
orientation/seams, exposure, sky appearance and runtime lighting behavior remain
unverified. File checks prove the bindings and preserved assets; they do not
prove the final rendered result. Current source tests: 106 run, 105 passed,
one existing data-dependent skip.
