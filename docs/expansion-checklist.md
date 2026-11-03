# Expansion acceptance checklist

File-level checks complete: accepted model geometry/material atlases and new references; unrelated serialized objects; original cat and entire audio bundle; existing MP7 objects; original operator texture bundles; legacy adoption hashes; rollback to the preceding mod stack; reinstallation; missing-source and stale-frontend rejection; source-only tests.

Remaining game-visible checks:
- [ ] Scorpion, Kar98k and P90 armory display, hipfire, ADS, reload and LODs.
- [ ] Tail/rod/prop clearance and original hand animation.
- [ ] Lynx full cat/tail, firing and meowing reload unchanged.
- [ ] MP7, gold attachments and custom magenta operators unchanged.
- [ ] Sky sun/clouds and cube seams on Warzone, Depot, Drains and Warehouse.
- [ ] HDR/exposure and actual lighting behavior unchanged; day/night coverage recorded.
- [ ] Frame-time comparison at the same 3840x2160 settings with background load controlled.
- [x] Current Windows installer window, Save action, 19-mod selections and both FMOD PCM rates in Windows 11 VM.
- [ ] Windows game installation and game runtime.
- [ ] Operator rigs: walking/running/jumping/sliding/aiming, weapon handling and helicopter introduction.

The corrected magenta Ranger/Stim pilot, matte materials, slimmer matching first-person arms, raised weapon visuals and 90-degree rod roll are installed and hash-verified. Shrek's shooting lens now uses the shipped transparent URP Lit shader; its material-only correction passed private apply/restore and all 81 managed bundle hashes verify. Fishguy remains optional. These file checks do not tick game-visible acceptance. Do not tick game-visible checks from source renders or file verification.

- [x] Native offline menu: Ranger uses the magenta Stim pilot and Dozer uses Shrek; default Ranger is not Fishguy.
- [ ] Other assignments and full character animations in-game.
- [ ] Shrek/Fishguy and other rebuilt characters no longer look metallic; rear surfaces have correct color.
- [ ] Matching first-person arms: actual hand grip, finger deformation, watch/weapon clearance and ADS/reload.
- [ ] Raised rod, nailer and toaster align acceptably with native sights.

- [ ] Shrek rust shooting lens: eyes visible through it, correct depth/sorting and head attachment in the helicopter introduction.
- [ ] Optional TF2 Medigun sound: actual firing loop, volume and spin behavior; Lynx meows unchanged.

November 3 runtime evidence: Shrek's eyes are visible through the rust lens in the native Dozer showcase. Helicopter attachment and sorting across poses remain unchecked. See [actual captures and limits](screenshots/README.md#current-operator-and-installer-runtime-checks--november-3). The stretched seal is intentional; do not precompensate its aspect ratio.
