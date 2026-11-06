# Local classic Minecraft sky importer

Development source can read a locally owned Minecraft Java client jar and adapt
its original clouds, sun, first moon phase and plains sky/fog palette to the
existing independent sky module. The original generated MWC sky remains the
default when the path is blank. The importer never executes Java or extracts
archive members to disk.

On Extras, enable the existing sky option and choose the client `.jar`. After a
successful apply, the path is remembered in `minecraft-source.txt`. Clearing the
field selects generated art again. Older frontends that omit this request field
retain the saved choice. Disabling the sky option or restoring originals uses
the existing manager transaction and does not require the source jar.

The selected jar must contain the classic cloud, sun and four-by-two moon-phase
PNG layout, the plains biome palette and `version.json`. Missing, duplicate or
oversized members, unsupported dimensions and a changed source fail explicitly.
A build manifest records the client version, jar/member SHA-256 hashes and
source colours. No credentials or downloads are required.

Only importer code is distributed. Client artwork and derived textures stay
local and must be generated outside the source tree. The Minecraft
[EULA](https://www.minecraft.net/en-us/eula) reserves distribution of Mojang
content; MWC does not claim a redistribution grant or bundle that content.

The adaptation is static: cloud movement, weather and a day/night cycle are not
implemented. The first moon phase can be rendered, but no nighttime Combat Master
environment has been accepted. Scene geometry, original sky/reflection textures,
lights and RenderSettings are preserved. Local-art mode normalizes only the
reviewed sky materials' `_Exposure` to 1.0 and `_Tint` to neutral 0.5 so the
original Minecraft colours remain readable. Other material properties are retained. Generated-art
mode preserves the original exposure and tint.

Validation on 2026-11-06: local Java 1.20.1 and 1.21.1 artwork loaded; private
day/night previews rendered from 1.20.1. Eight real bundle outputs reopened and passed object/texture
verification (11 materials, including two six-sided skies and twelve 2D faces).
The Linux Extras tab rendered with a saved jar path. A disposable private
manager fixture applied/removed all eight outputs and restored every original
hash without requiring the client jar during restoration. The source suite passed
156 tests with one existing skip; eight focused tests also passed in Windows
embedded Python 3.12.10 under Wine. The initial native Parvis review showed square
clouds but muted colours at original exposure. Exposure alone then clipped the sky. The game shader's
neutral tint (0.5) and exposure (1.0) produced bright blue sky, distinct square
clouds and an isolated square sun in a fresh stationary Parvis test. Those
settings apply only to local-art mode and are recorded/verified per material.

The [native capture hashes](minecraft-local-sky-native-verification.json) and
[bundle verification](minecraft-local-sky-bundle-verification.json) are recorded
separately. The game exited with code 0; Gamescope teardown returned 139, so
these runs do not establish general stability.

The native check used a copied guest profile, read-only asset mounts, NVIDIA
Vulkan and a 1280×720 headless display with a 30 FPS test cap. It sent only menu
and bounded camera-look inputs. The tested Parvis bundle used original map
surfaces, rather than the installed halftone terrain, so that initial run alone
did not establish native coexistence with installed terrain. A later private overlay test confirmed local sky, halftone terrain,
magenta Grapple arms and gold weapon/attachments together on Parvis; see the
[coexistence capture hashes](minecraft-local-sky-coexistence-verification.json).
Day/night cycling, nighttime, native six-sided orientation/seams, a full
saved-selection rebuild, all-map coverage and 4K performance remain unaccepted. Tests and previews are not full in-game acceptance. This importer is included in
[v0.1.5-preview](https://github.com/aridlin/combat-master-MWC-magenta-war-crimes/releases/tag/v0.1.5-preview).

Separate Linux and Windows installer candidates were built from source commit
`5a9373d`. The [package hashes and runtime checks](minecraft-local-sky-installer-verification.json)
record 167/168 matching source files, actual Linux backend apply/restore of all
eight real bundles, and eight packaged Windows importer tests under Wine. The
Windows Extras field was visually reviewed under Wine, not native Windows.
Candidate archives exclude local Minecraft artwork, M1A0, Valve and Respawn
imports. The personal installer was not replaced. All 81 installed bundles and
81 original backups still match their recorded hashes.

The later Parvis coexistence candidate was built over three hash-verified
installed map bundles, preserving every non-sky object byte-for-byte. It was
mounted read-only in a copied-profile private native session; the actual
installation was not updated. Fuji was also opened, but its observed roof/small
sky opening does not establish source-art or six-sided orientation acceptance.
The same results screen showed the existing ginger Lynx cat on a native operator
weapon, adding a limited world-view check rather than reload/ADS acceptance.
