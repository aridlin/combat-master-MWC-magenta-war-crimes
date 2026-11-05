# Optional local Audiojungle excerpts

`audiojungle_medigun` adds four fixed sound excerpts from the user's local
[CoopDogger Audiojungle TF2 pack](https://github.com/CoopDogger/Audiojungle).
It is an independent Extras option. It can accompany the Medigun visual or be
used with the original Minigun. It does not change any Lynx sound.

Extract the original TF2 `AudioJungle.7z` with a trusted archive utility. In
Extras, enter the extracted `audiojungle` directory that contains `sound/`.
Select **Audiojungle excerpts / Minigun**, then apply in an offline or expressly
authorized environment with Combat Master closed. Do not select the vanilla
**TF2 Medigun sounds / Minigun** simultaneously: both own the same four native
slots, and the manager reports this conflict before creating a build or
changing any game asset. The source directory is remembered after a successful
apply. A partial source folder containing the four mapped files is sufficient.

The readable `config/audiojungle-map.json` chooses `medigun_heal1.mp3`,
`medigun_heal2.mp3`, `medigun_heal3.mp3` and `medigun_charged.wav` under
`sound/ui/weapons/medigun/`. Each row includes its native clip ID, name and
source offset. Offsets select excerpts; they do not extend native clip timing.
The MP3 streams are decoded through the existing FMOD library with its output
device disabled. No sound-definition script, configuration or executable from
the source pack is run.

This deliberately describes the actual implementation: four fixed excerpts,
not TF2's thousands of randomized event variants. Existing Combat Master
firing and barrel-spin events trigger the original slots. The replacement
retains each native duration, frame count, channel count, frequency, pitch,
load and spatial/event metadata. Stereo-to-mono conversion, anti-aliasing when
resampling, RMS matching, a peak ceiling and short edge fades use the same
writer as the vanilla TF2 option. All source hashes and exact excerpts are
recorded in the private build manifest.

The writer appends new samples, preserves the complete existing resource bank
as an exact prefix, checks all unrelated serialized objects, and independently
decodes each resulting FSB container to require exact PCM equality. A private
composition test preserved all seven existing Lynx FSB sample hashes, rebuilt
the vanilla TF2 option successfully, and returned to the exact baseline bundle
when Audiojungle was deselected. The host installation was unchanged.

Status: clean source tests pass (139 run, one skip). Real private Linux and
Windows-runtime bundle builds pass, and the packaged Windows runtime passes
10 focused audio tests under Wine. Linux GUI source-field/card checks pass. In-game
balance, repeated-fire sound quality and performance remain untested. This
option has not been enabled in the user's game. Private source decoding and
waveform checks are not an in-game audition.

No source audio, source archive, sound scripts or generated game bundle is
redistributed. MWC does not grant a license to the pack's mixed-source content.
Use a locally obtained copy under its applicable terms.

To remove it, deselect the option and apply the remaining mods with the game
closed. The manager rebuilds from verified originals. Restore all originals
removes the complete managed selection. Retain the state directory and its
backups until restoration finishes.

Cross-platform comparison retained exact native rates and frame counts. The
three MP3-derived excerpts differed by at most one PCM16 unit between the
Linux and Windows FMOD builds; the WAV-derived spin sample matched exactly.
Each platform independently passed exact container-to-PCM roundtrip checks.
