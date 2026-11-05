# Expansion acceptance checklist

File-level checks complete: accepted model geometry/material atlases and new references; unrelated serialized objects; original cat and entire audio bundle; existing MP7 objects; original operator texture bundles; legacy adoption hashes; rollback to the preceding mod stack; reinstallation; missing-source and stale-frontend rejection; source-only tests.

Remaining game-visible checks:
- [x] Native offline armory/showcase appearance for Scorpion, Kar98k fishing rod, MP7 nailer and P90 toaster.
- [ ] Their first-person hipfire, ADS, reload, sight alignment and LOD appearance.
- [ ] Tail/rod/prop clearance and original hand animation.
- [ ] Lynx full cat/tail, firing and meowing reload unchanged.
- [ ] MP7, gold attachments and custom magenta operators unchanged.
- [ ] Sky sun/clouds and cube seams on Warzone, Depot, Drains and Warehouse.
- [ ] HDR/exposure and actual lighting behavior unchanged; day/night coverage recorded.
- [ ] Frame-time comparison at the same 3840x2160 settings with background load controlled.
- [x] Current Windows installer window, Save action, then-current mod selections and both FMOD PCM rates in Windows 11 VM.
- [ ] Windows game installation and game runtime.
- [ ] Operator rigs: walking/running/jumping/sliding/aiming, weapon handling and helicopter introduction.

The corrected magenta Ranger/armored human Grapple pilot, matte materials, slimmer matching first-person arms, raised weapon visuals and 90-degree rod roll are installed and hash-verified. Grapple supersedes the earlier Stim default; legacy Stim remains optional. Shrek's shooting lens now uses the shipped transparent URP Lit shader; its material-only correction passed private apply/restore and all 81 managed bundle hashes verify. Fishguy remains optional. These file checks do not tick game-visible acceptance. Do not tick game-visible checks from source renders or file verification.

- [x] Native offline menu: Ranger uses the magenta armored human Grapple pilot and Dozer uses Shrek; Fishguy remains optional.
- [x] Native installed-stack stationary first-person check: Grapple arms and square-cloud sky on Parvis.
- [x] Rejected the private Fishguy hand-driver remap after shipped-clip comparisons exposed palm/finger stretching; production fitter restored, retired probe disabled.
- [ ] Baseline Fishguy hand grip and a suitable correction: native in-game appearance. The running normal game prevents concurrent private GPU validation; numerical tests alone do not establish visual acceptance.
- [ ] Other assignments and full character animations in-game.
- [ ] Shrek/Fishguy and other rebuilt characters no longer look metallic; rear surfaces have correct color.
- [ ] Matching first-person arms: actual hand grip, finger deformation, watch/weapon clearance and ADS/reload.
- [ ] Raised rod, nailer and toaster align acceptably with native sights.

- [ ] Shrek rust shooting lens: eyes visible through it, correct depth/sorting and head attachment in the helicopter introduction.
- [ ] Optional TF2 Medigun sound: actual firing loop, volume and spin behavior; Lynx meows unchanged.

November 3 runtime evidence: Shrek's eyes are visible through the rust lens in the native Dozer showcase. Helicopter attachment and sorting across poses remain unchecked. See [actual captures and limits](screenshots/README.md#current-operator-and-installer-runtime-checks--november-3). The stretched seal is intentional; do not precompensate its aspect ratio.

November 5 audio development checks:
- [x] Independent Audiojungle Extras card and remembered local source path; Linux GUI checked without Apply.
- [x] Four reviewed native slots only; explicit conflict with vanilla TF2 Medigun sounds before building.
- [x] Real private Linux and Windows-runtime bundle builds; exact unrelated object/resource-prefix verification and PCM/FMOD roundtrip.
- [x] All seven existing Lynx samples preserved and exact baseline restored on deselection.
- [x] Clean development Linux/Windows packages contain the importer, omit private audio and omit the unverified hand candidate.
- [ ] Native in-game Audiojungle audition, repeated-fire balance and performance. Not applied to the user installation; not part of v0.1.4-preview downloads.

The clean Audiojungle source suite passes 139 tests (138 pass, one data-dependent skip). The Windows embedded runtime passes 10 focused audio tests under Wine and builds an actual private audio bundle. These checks do not establish native Windows game compatibility. Linux/Windows MP3-derived excerpts differ by at most one PCM16 unit in the measured comparison; rates and frame counts agree and each platform independently passes exact FMOD roundtrip. The original WAV-derived barrel-spin sample matches across both platforms.
