# MWC modular installer (preview)

The native Windows and Linux interface uses the user's FT C++17 library. Each card has an independent selection and an explicitly labeled thumbnail. Select Lynx, Scorpion, Kar98k, MP7, P90, player textures, weapon textures, terrain/environment, Lynx cat sounds, blue crates, Sun reticles, the Steg Spikes iron sight, clear helicopter glass, the Fishguy menu, or the Minecraft-style sky independently. Three weapon choices now use imported authored models; the MP7 remains explicitly on its existing prototype pending a suitable source asset.

Opening the installer does not install mods. Apply builds a complete desired selection from immutable original snapshots; removing one choice preserves the other enabled choices. Restore all originals removes the managed selection. Close Combat Master before applying or restoring. Use these visual experiments offline or in an explicitly authorized environment.

The bundled edition includes the original M1A0 archive requested by the user and selects it automatically. Its credits and hash are in `addons/M1A0-CREDITS.txt`; MWC's MIT license does not apply to third-party content. Only inspected visual/WAV inputs are imported. Addon Lua is never executed.

## Run

Extract the entire distribution. On Linux run `./MWC-Installer`; on Windows run `MWC-Installer.exe`. Keep all adjacent runtime/assets folders. No Python installation is needed for the packaged distributions. Linux requires Cairo and X11 libraries and runs through Xwayland on KDE Wayland. The GUI is forced to native mode; it does not start FT's web server.

The default window is 1180 x 1400 with a 128-pixel seal. Game detection reads Steam library records (including Windows registry Steam roots). You can enter the Combat Master game directory manually. Current build guard: 24397779, Unity 6000.3.19f1. Windows game-bundle compatibility remains experimental and has not been validated against a Windows game installation.

Persistent backups, selections and logs are under `~/.local/share/combat-master-mwc` (or `$XDG_DATA_HOME/combat-master-mwc`) on Linux, and `%LOCALAPPDATA%\CombatMasterMWC` on Windows. `--state DIRECTORY` selects another directory. Do not delete backups before restoration. Previously installed legacy MWC layers need their verified original snapshots imported first; they must not be treated as pristine game files.

## Build

Install Python 3.12 dependencies from the repository's `requirements.txt`. Install PyInstaller for Linux packaging. `python installer/build_frontend.py` compiles the Linux frontend with `pkg-config cairo x11`; add `--windows` to cross-compile with MinGW-w64. The FT header is pinned in `vendor/PROVENANCE.md`.

`python installer/package.py` creates the Linux portable distribution. `python installer/package.py --windows` creates the Windows distribution from the official CPython 3.12.10 embeddable ZIP in `installer/downloads/`, dependency wheels in `win-wheels/` and `pure-wheels/`, and the local M1A0 archive at `external-assets/m1a0/M1A0-Cat-Gun.bin`. Downloads are build inputs, excluded from Git. Runtime distributions retain dependency license/metadata files. The Linux packager clears only the executable-stack flag on private ELF runtime copies when present, because current glibc rejects the portable CPython build's unnecessary executable-stack request.

The menu builder in `tools/menu_artwork.py` takes an original extracted LobbyBG2 PNG and the supplied sticker. It produces a deterministic grayscale AM halftone at original dimensions, with a file-hash provenance record. It does not redraw the original scene or use AI generation.

## Recovery and verification

The installer verifies every original/installed bundle hash before committing. Each replacement uses a temporary sibling file, fsync and an atomic replace. A write-ahead journal and verified undo copies allow recovery after an interrupted multi-file commit. An OS file lock prevents concurrent installers. Changed game files or modified backups stop installation instead of overwriting newer data. After a crash, rerun the same request/state directory to recover first. Never manually remove `pending.json` to bypass recovery.

Source tests: `PYTHONPATH=. python -m unittest discover -s tests -q`.

The local integration helper `installer/integration.py TEST_DIRECTORY ORIGINAL_BUNDLE_DIRECTORY` checks Scorpion-only, Scorpion+MP7, MP7-only, and the combined crates/sights/glass/menu modules against private copies. It needs local original game files and never modifies the installed game. Unit tests also simulate a partial commit failure, interrupted-commit recovery, external changes, exclusive locking, and thumbnail coverage. These checks do not prove actual gameplay, animation, reticle alignment or frame-rate behavior.

Test before release: verify every card/toggle on both desktops; apply two mods sharing a bundle; remove one and inspect the remaining mod; restore and compare all original hashes; test 4K hipfire/ADS/reload/LOD in an authorized environment; test category-only texture selections and terrain arrays; check disk/VRAM requirements and frame times. Windows runtime imports were tested in the user's VM; Windows UI and game installation tests remain pending.

Expansion asset checks: run `backend/mwc-backend --diagnose` in the Linux distribution to verify the packaged model assets and sky generator without changing game files. See [the expansion report](../docs/expansion.md) for all incomplete/blocked character features.
