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

These changes are newer than the v0.1.2 binaries and are included in v0.1.3.
The local six-bundle pilot/sky update is now installed, with all original/undo
hashes verified and all unrelated weapon/audio files retained exactly. A network-isolated native Linux Parvis test on 2026-11-04 now visibly shows the
new blue sky and square cloud shapes at several stationary camera angles. The
map's original material tint/exposure remains in place, producing more subdued
colors than the source image. This confirms the Parvis cubemap replacement,
not every map: actual native six-sided orientation/seams, square sun/moon and
broader lighting review remain pending. No movement or firing inputs were sent.
The game exited with code 0; Gamescope returned 139 during shutdown, and the
host profile stayed unchanged. The capped 1280x720 run is not a 4K benchmark.
Current source suite: 130 tests, 129 passed and one existing data-dependent skip.
