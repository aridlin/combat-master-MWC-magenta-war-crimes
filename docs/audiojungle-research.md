# Audiojungle source investigation

The requested project is CoopDogger's [Audiojungle TF2 soundpack](https://github.com/CoopDogger/Audiojungle),
also listed on [GameBanana](https://gamebanana.com/wips/90778). The author's
`Release` tag provides `AudioJungle.7z`; the separate `Payday_2_WIP` tag is a
different port and was not used as the TF2 source.

The original public TF2 archive was downloaded for private inspection:
1,443,055,415 bytes, SHA-256
`d441a35b2452716568f513f9d255f933660ba28d47397ff822fca9f6f51305ba`.
Its inventory contains 3,123 MP3s and 677 WAVs. Thirty sound-definition text files
were read as data; no CFG, script or executable was run. No login was needed.

The Medigun definitions use TF2 `rndwave` event lists. The corresponding folder
has 371 sound files, including healing, detach and other variants. Three sampled
healing MP3s decode to stereo PCM16 at 44.1 kHz, each about 4.05 seconds, through
the existing FMOD library with output disabled. Their initial half seconds have
audible signal according to waveform measurements; this is not a listening or
in-game quality test.

Combat Master's reviewed Minigun slots are only about 0.50 seconds for firing
and 0.83 seconds for barrel spin. Static asset replacement can put selected
excerpts into those slots. It cannot import TF2's event scripts or give the game
thousands of randomized variants without an additional supported interface.
Extending each shot to a full four-second clip could produce overlapping sounds
and would change the current timing behavior. That has not been implemented.

No redistribution grant for this mixed-source archive has been recorded. MWC
does not ship the archive, sampled sounds or its scripts. The independently
implemented local **vanilla TF2 Medigun sound** option remains separate.

The subsequent [local Audiojungle excerpt importer](audiojungle-local-import.md)
now implements four fixed samples with explicit slot-conflict handling and the
same timing-preserving writer. Actual private-bundle composition, Lynx sample
preservation and exact deselection passed. This is not the entire randomized
TF2 sound-event system; in-game sound quality and playback cost remain untested.
