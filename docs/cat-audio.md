# Lynx cat sounds — audio only

The module imports cat sound samples from the user's local M1A0 addon. The
seven existing GM6Lynx AudioClip slots keep their names, IDs, duration, pitch,
channel count, sample rate, preload and 3D/spatial metadata. Animations,
firing rate, recoil, spread, ammo, event bindings and reload mechanics are
not modified.

| Original slot | Addon source |
| --- | --- |
| Shoot1 | catgun_fire01.wav |
| Shoot2 | catgun_fire03.wav |
| Shoot3 | catgun_fire08.wav |
| MagOut | catgun_reload00.wav |
| MagIn | catgun_reload.wav |
| BoltOpen | catgun_fire04.wav |
| BoltClose | catgun_fire05.wav |

Each source is downmixed to mono and an audible continuous window is fitted
to the existing slot's exact sample count. No time stretch or pitch shift is
used. A five-millisecond edge fade avoids clicks. These are actual addon cat
sounds fitted to Combat Master's event slots, not the original GMod animation
or its eight-variation/timeline implementation. The native game's existing
three shot variations and event scheduling remain unchanged.

New PCM16 FSB5 samples are appended to the existing audio resource. Original
resource bytes remain an exact prefix; unrelated audio clips retain their
original data and offsets. Only the seven selected resource offsets/sizes
change. The FSB5 encoding follows the layout also documented by
[vgmstream's FSB5 reader](https://github.com/vgmstream/vgmstream/blob/master/src/meta/fsb5.c).

Verification reopens the bundle, checks all other object bytes and original
resource bytes, and decodes every new sample through the installed FMOD
toolkit in NOSOUND mode. Decoded frame counts and PCM waveforms match exactly.
No desktop audio is played during verification. In-game audibility, balance
and event synchronization still need an offline audition.

```sh
# First import the local addon using the M1A0 import guide.
.venv/bin/python cat_audio.py prepare
.venv/bin/python cat_audio.py build
.venv/bin/python cat_audio.py verify
.venv/bin/python cat_audio.py install --dry-run
.venv/bin/python cat_audio.py install
.venv/bin/python cat_audio.py restore
```

Keep source WAVs, previews, backups and manifests local. Third-party addon
sounds are not redistributed under this repository's MIT license. The audio
layer affects root/audio, independently of the visual layers. Restore it
before restoring the full underlying installation.
