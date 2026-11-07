# Optional local TF2 Medigun sounds

The independent `tf2_medigun_audio` Extras choice reads `medigun_heal.wav` and
`medigun_charged.wav` from the user's local `tf2_sound_misc_dir.vpk`. It changes
only three Minigun firing clips and the barrel-spin clip in `root/audio`.
The Medigun visual and this audio option can be selected independently.

Development source adds **Preview sounds** on the Extras card. It exports
and opens a private audition without applying the mod or closing the game.
See [audio previews](audio-previews.md).

These are Valve game assets, not MWC MIT content. No Valve WAV, VPK, model or
compiled replacement game bundle is distributed. A local TF2 installation is
required; Steam discovery or the installer's TF2 folder field supplies it.
The importer verifies VPK entry CRCs and executes no game scripts.

`config/tf2-audio-map.json` pins exact native clip IDs and names to build
24397779. Offline processing averages stereo to mono, resamples without changing
pitch, uses anti-alias filtering when downsampling, fits the exact native frame
count and matches the original slot's RMS level with a peak limit and short
edge fades. Native rates remain 44.1 or 22.05 kHz. Playback events, load settings,
pitch, spatial parameters, timing and gameplay data stay unchanged. There is no
runtime audio processor or injected code.

Each replacement is appended to the resource bank. Its complete existing bytes
remain an exact prefix. Every unrelated serialized object is byte-checked;
changed clips allow only resource offset/size changes. FMOD decoding must return
the exact expected PCM samples. File verification does not establish how short
Medigun snippets will sound under the game's actual firing loop.

The private composition test enabled cat audio plus Medigun audio, then removed
only Medigun audio. All seven Lynx sample hashes stayed exact, and the resulting
cat-only bundle returned to SHA-256
`552fa9b28d9381886672e5f9aa2fc32ff6235496baf7364a480f1061368b3053`.
Installed game files were not modified by that test. In-game audition, balance
and repeated-fire loop quality remain untested.

To remove this option after installing a future build that includes it, close
Combat Master, deselect its card and apply the remaining selection. The manager
recomposes from verified originals, retaining selected Lynx sounds and other
mods. **Restore all originals** removes the complete managed selection. Keep
the state directory and backups until restoration finishes.
