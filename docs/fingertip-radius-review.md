# Preserve fitted fingertips during viewmodel slimming

The source arm fitter now carries the native fingertip cap direction through
the later radius-reduction pass. Previously that pass reused the previous
finger joint's axis, moving an already fitted cap by up to 7.3 mm in the native
Ranger reference. This affects the nine TF2 arm options, whose hand radius is
reduced to 70%. Fishguy uses a hand radius of 100%; its positions and normals
remain byte-identical. Other operator models retain their existing fitting path.

The first direct axis substitution introduced extra reversed rest faces at
some authored finger transitions and was rejected. The implemented correction
keeps the old frame at the leaf base and blends to the cap frame using a
smoothstep along the distal segment. The normal transform includes the spatial
derivative of this blend. A finite-difference test checks that differential;
separate fixtures check the off-axis endpoint, radial reduction, protected base,
invalid input and byte-identical unit-scale/default paths.

Both native arm meshes for all nine TF2 classes pass source fitting and retain
their UVs, topology, skin indices and weights. Non-distal positions remain exact.
No new faces oppose their pre-radius geometric normal in these comparisons.
This is a scoped rest-shape diagnostic, not proof of a deformation-free mesh.
Existing crossings remain: Heavy removes six strict crossing pairs and adds
three; the other classes retain their previous crossing pairs. The check excludes
adjacent welded faces, coplanar overlap and boundary-only contact. All nine
classes have now received the scoped native pose review below. The rest-surface
crossings and full animation quality remain open.

## Native review and distribution

Fresh native Linux Vulkan stationary MP.V captures compare the original and
smooth Medic and Scout builds in hipfire, ADS and return to hipfire. The distal
thumb sits closer around the weapon in ADS; Scout's two protruding fingertip
lobes are mostly tucked behind it. The sight center stays clear. The authored
Medic open cuff and existing wrist issues remain. This is a localized grip
improvement, with full animation acceptance still open.

![Scout before radius correction](screenshots/scout-radius-before-ads-nov6.png)

![Scout after smooth radius correction](screenshots/scout-radius-after-ads-nov6.png)

![Medic before radius correction](screenshots/medic-radius-before-ads-nov6.png)

![Medic after smooth radius correction](screenshots/medic-radius-after-ads-nov6.png)

[The evidence index](fingertip-radius-verification.json) records all four paired
native runs, exact bundle/capture hashes, source comparisons and the rejected
abrupt-axis candidate. Native games exited 0; Gamescope teardown returned 139
separately. All four host-profile preservation checks passed.

The [remaining seven-class review](fingertip-radius-all-class-native-verification.json)
adds fourteen paired native runs for Heavy, Soldier, Pyro, Demoman, Engineer,
Sniper and Spy. Their hipfire, ADS and return captures were inspected individually.
The corrected fingertips protrude less beside the MP.V, and the sight center
stays clear. Existing wrist/cuff transitions remain. All fourteen games exited
0 and preserved the host profile; Gamescope teardown returned 139 separately.
An interrupted Soldier attempt ended before ADS and is excluded from acceptance.

![Heavy corrected ADS](screenshots/heavy-radius-after-ads-nov7.png)

![Engineer corrected ADS](screenshots/engineer-radius-after-ads-nov7.png)

The tests use the official empty range with copied guest profiles, network
isolation, no host display/audio, no movement or firing and unchanged installed
quality/player data. No private skin-quality override is used. These are actual
native game captures, not Editor renders or performance measurements.

[v0.1.10-preview Linux and Windows packages](https://github.com/aridlin/combat-master-MWC-magenta-war-crimes/releases/tag/v0.1.10-preview)
include this change and retain the
small-screen window fix. The frozen Linux backend reproduces the reviewed Heavy
bundle on disposable real-bundle copies and restores both originals without TF2
available. The Windows embedded runtime passes 21 focused tests under Wine.
Its full Fishguy apply/restore transaction on disposable Linux asset copies also
produces a byte-identical first-person bundle and restores both originals.
That does not validate native Windows game assets or gameplay.
[Package evidence](fingertip-radius-installer-verification.json) separates these
checks from native game acceptance. The personal portable installers are also
updated, with exact `.before-radius-v1` rollback folders and the local M1A0
archive preserved. v0.1.9-preview packages contain the earlier fitting.

Installed game bundles, selections and backups are unchanged. The source suite
runs 181 tests: 180 pass and one existing data-dependent test is skipped.
Other weapons/attachments, movement, reloads, helicopter appearance, 4K
performance and native Windows game acceptance remain unverified. The Fishguy
wrist remains a separate investigation.
