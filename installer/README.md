# MWC modular installer (preview)

The native Windows and Linux interface uses the user's FT C++17 library. Weapon, texture and extra cards are independently selectable. All four earlier weapon placeholders now use authored models; Minigun can use the actual Medigun imported from a local TF2 installation. The Operators tab assigns Shrek, Fishguy, Mario, Minecraft Steve, the legacy Titanfall Stim pilot, locally prepared armored Grapple and female Pulse Blade pilots, or any of the nine locally imported TF2 mercenaries to individual game operators. Pending models are labeled and cannot silently substitute a placeholder.

Opening the installer does not install mods. Apply builds a complete desired selection from immutable original snapshots; removing one choice preserves the other enabled choices. Restore all originals removes the managed selection. Close Combat Master before applying or restoring. Use these visual experiments offline or in an explicitly authorized environment.

Public releases import a locally owned M1A0 archive through the file chooser. The separate locally bundled edition includes the archive requested by the user and selects it automatically. Its credits and hash are in `addons/M1A0-CREDITS.txt`; MWC's MIT license does not apply to third-party content. Only inspected visual/WAV inputs are imported. Addon Lua is never executed.

## Run

Extract the entire distribution. On Linux run `./MWC-Installer`; on Windows run `MWC-Installer.exe`. Keep all adjacent runtime/assets folders. No Python installation is needed for the packaged distributions. Linux requires Cairo and X11 libraries and runs through Xwayland on KDE Wayland. The GUI is forced to native mode; it does not start FT's web server.

The default window is 1180 x 1400 with a 128-pixel seal. Game detection reads Steam library records (including Windows registry Steam roots). You can enter the Combat Master game directory manually. Current build guard: 24397779, Unity 6000.3.19f1. Windows game-bundle compatibility remains experimental and has not been validated against a Windows game installation.

Persistent backups, selections and logs are under `~/.local/share/combat-master-mwc` (or `$XDG_DATA_HOME/combat-master-mwc`) on Linux, and `%LOCALAPPDATA%\CombatMasterMWC` on Windows. `--state DIRECTORY` selects another directory. Do not delete backups before restoration. Previously installed legacy MWC layers need their verified original snapshots imported first; they must not be treated as pristine game files.

## Build

Install Python 3.12 dependencies from the repository's `requirements.txt`. Install PyInstaller for Linux packaging. `python installer/build_frontend.py` compiles the Linux frontend with `pkg-config cairo x11`; add `--windows` to cross-compile with MinGW-w64. The FT header is pinned in `vendor/PROVENANCE.md`.

`python installer/package.py` creates the Linux portable distribution. `python installer/package.py --windows` creates the Windows distribution from the official CPython 3.12.10 embeddable ZIP in `installer/downloads/`, dependency wheels in `win-wheels/` and `pure-wheels/`, and the local M1A0 archive at `external-assets/m1a0/M1A0-Cat-Gun.bin`. Downloads are build inputs, excluded from Git. Runtime distributions retain dependency license/metadata files. The Linux packager clears only the executable-stack flag on private ELF runtime copies when present, because current glibc rejects the portable CPython build's unnecessary executable-stack request.

The menu builder in `tools/menu_artwork.py` takes an original extracted LobbyBG2 PNG and the supplied sticker. It produces a deterministic grayscale AM halftone at original dimensions, with a file-hash provenance record. It does not redraw the original scene or use AI generation. The in-game seal intentionally keeps the original background stretch, as requested by the user.

## Recovery and verification

The installer verifies every original/installed bundle hash before committing. Each replacement uses a temporary sibling file, fsync and an atomic replace. A write-ahead journal and verified undo copies allow recovery after an interrupted multi-file commit. An OS file lock prevents concurrent installers. Changed game files or modified backups stop installation instead of overwriting newer data. After a crash, rerun the same request/state directory to recover first. Never manually remove `pending.json` to bypass recovery.

Source tests: `PYTHONPATH=. python -m unittest discover -s tests -q`.

The local integration helper `installer/integration.py TEST_DIRECTORY ORIGINAL_BUNDLE_DIRECTORY` checks Scorpion-only, Scorpion+MP7, MP7-only, and the combined crates/sights/glass/menu modules against private copies. It needs local original game files and never modifies the installed game. Unit tests also simulate a partial commit failure, interrupted-commit recovery, external changes, exclusive locking, and thumbnail coverage. These checks do not prove actual gameplay, animation, reticle alignment or frame-rate behavior.

Test before release: verify every card/toggle on both desktops; apply two mods sharing a bundle; remove one and inspect the remaining mod; restore and compare all original hashes; test 4K hipfire/ADS/reload/LOD in an authorized environment; test category-only texture selections and terrain arrays; check disk/VRAM requirements and frame times. The v0.1.0 Windows GUI, saved selections, backend diagnostics and FMOD initialization were tested in the user's Windows 11 VM. Windows game installation and gameplay remain untested.

Expansion asset checks: run `backend/mwc-backend --diagnose` in the Linux distribution to verify the packaged model assets and sky generator without changing game files. See [the expansion report](../docs/expansion.md) for all incomplete/blocked character features.


Operator choices are saved separately from installed state. Apply selected mods composes those assignments too. The TF2 folder can be detected through Steam or entered on the Operators tab; Import TF2 previews reads local assets and generates private thumbnails without changing game files. See OPERATOR-ASSET-CREDITS.md and operator-licenses/ in the distribution. Character prototypes have passed file/synthetic checks; in-game acceptance remains pending.

Operator colors: each replacement model has its own Magenta checkbox. A separate toggle controls unreplaced native game operator models; matching authored first-person arms are independently selectable; otherwise they follow Player textures. Source colors remain the default for Shrek, Fishguy, Mario and Steve. Save choices and colors does not install anything.

Matching first-person arms is an optional control on the Operators tab and an Extras card. It uses actual source arm geometry on the unchanged native weapon-animation rig. Shared-prefab assignment conflicts fail explicitly. Ranger/pilot and Dozer/Shrek arm builds are file-verified; ADS grip, clipping and reload appearance still need in-game testing. Explicit non-metallic/flat-normal data textures and root-bone-space renderer bounds apply to rebuilt character models.

Use `--output DIRECTORY` when packaging to keep an already running distribution intact.

First-person volume is configurable independently in `config/operator-viewmodels.json` (portable Linux: `backend/_internal/config/`; Windows: `source/config/`). The scales reduce arm/hand radius around native joint axes while retaining reach. Rebuild/apply after editing. Third-person geometry stays unchanged.

Sonic spin ball is an independent weapon-model card for the impact grenade. Held and thrown visual bindings are isolated; original shared launcher meshes, projectile/physics/damage and all audio remain unchanged. This option has passed private shared-bundle composition and removal tests, with in-game testing pending. See WEAPON-ASSET-CREDITS.md and weapon-licenses/.

Public release builds use `python installer/package.py --without-addon` (add `--windows` for Windows). This edition excludes the M1A0 archive because MWC has no recorded redistribution grant; local import remains supported. The default local build retains the requested bundled edition.

Development source adds an independent **TF2 Medigun audio** Extras card. It reads only a local TF2 installation and bundles no Valve sound data. Three Minigun firing slots and barrel spin keep their native durations and event metadata. Disabling it preserves Lynx cat audio. This newer option has private file/composition verification and Windows VM selection/PCM decoding checks; in-game audition remains pending.

Fishguy uses an anatomical palm-width fit with a smooth distal-forearm transition.
It preserves source topology/UVs/skin weights and native skeletons. His first-person
hands keep radius 1.0 after this fit; arms retain radius 0.60. Native menu appearance
and serialized/synthetic checks passed; actual first-person grip and full animation
acceptance remain pending. This applies only when Fishguy is selected, and does not
assign him to Ranger or any other default automatically.

Native Titanfall pilots have a prepared-source import control on the Operators
tab. Importing verifies and privately caches sources and previews, leaving the
installed selection and assignments unchanged. No EA assets are bundled. See
[the native pilot workflow](../docs/titanfall-native-import.md) for preparation,
revision backups, separate model choices and the remaining decoder/gameplay gates.
The packager now compiles the matching frontend before bundling the backend.

The native pilot prepared-source workflow passed Linux and Windows GUI
import/save checks, including re-import while previews are loaded. The frontend
releases preview image handles before import and reloads them after either
success or failure; this avoids Windows PNG replacement locks. Windows game
installation/editing is still untested.

The installer fits its startup window to the monitor under the pointer, reserving space for the title bar and desktop panels. Small displays use the existing vertical scrollbar; the window remains resizable.

The optional **Audiojungle excerpts / Minigun** Extras card reads an extracted local Audiojungle folder containing `sound/`. It preserves native slot durations and Lynx sounds; selecting it together with vanilla TF2 Medigun audio produces an explicit conflict. Source audio is not bundled. See [local import and verification](../docs/audiojungle-local-import.md). In-game audition remains pending.
