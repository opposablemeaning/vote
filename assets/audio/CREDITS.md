# Audio credits and licenses

All sound effects and music in `assets/audio/sfx/` and `assets/audio/music/` are synthesized from scratch by `scripts/sfx.py` and `scripts/music.py` (original work, no samples).

Field recordings used (license verified on the Freesound page, 2026-10-09):

| File | Source | Author | License |
|---|---|---|---|
| `cc0/no-kings-chants-870537.wav` | https://freesound.org/people/CHallSmith/sounds/870537/ ("No Kings Rally. Crowd chants slogans. 'Democracy' 'No Kings.'") | CHallSmith | CC0 1.0 |
| `cc0/crowd-cheers-870542.wav` | https://freesound.org/people/CHallSmith/sounds/870542/ ("No Kings Rally. Cheering supportive crowd with car horns.") | CHallSmith | CC0 1.0 |

Converted from Freesound's HQ MP3 previews (48 kHz mono WAV). CC0 requires no attribution; credited anyway as a courtesy.

The hero mix uses 870537 from 46.45 s ("No kings!") into "This is what democracy looks like!" (from ~55 s).

Drum samples (for the drum-kit options in `scripts/kits.py`):

| Folder | Source | Author | License |
|---|---|---|---|
| `cc0/drums/` | Freesound pack 32722, "Fractanimal_Acoustic_Drum_Kit_One_Shots" (https://freesound.org/people/johnnydekk/packs/32722/), from the HQ OGG previews | johnnydekk | CC0 1.0 (verified on each sound's page, 2026-10-09) |
| `cc0/tr808/` | Roland TR-808 Sound Sample Set 1.0.0 (1994), via https://github.com/tidalcycles/sounds-tr808-fischer (commit 85fbecf) | Michael Fischer, Technopolis | CC0 1.0 (`cc0/tr808/LICENSE-CC0.txt`) |

Samples used by the hero soundtrack's sound effects (`scripts/sfx_organic.py`) besides the drums and TR-808 above:

| Source | Author | License |
|---|---|---|
| https://github.com/cleary/samples-cello-plucked (body knocks `10_body_low`, `11_body_high`) | Trevor Exter (cello), Bernard Gray | CC0 1.0 (repo `LICENSE`, checked 2026-10-10) |

`scripts/track_engines.py` can also load cleary's `samples-cello-bowed` and `samples-flbass` (both CC0 1.0); the hero's music doesn't use them. The music itself is synthesized.

Data: protest locations from the Crowd Counting Consortium US Protest Event Data v18 (Harvard Ash Center / UConn), doi:10.7910/DVN/RI9JFU — CC0 1.0.
