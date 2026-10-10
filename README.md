# VOTE. THEM. OUT.

**The case against Trump and the GOP, one sourced receipt at a time: [opposablemeaning.com/vote](https://opposablemeaning.com/vote/)**

Every receipt links to its source and carries a label that says what kind of evidence it is: their own words, a court ruling, an official record, news reporting, data or an estimate. The list is public, so anyone can add to it and anyone can correct it.

**Election Day is Tuesday, Nov 3, 2026. [Check your registration at vote.org.](https://www.vote.org/am-i-registered-to-vote/)** Problems voting? Call 866-OUR-VOTE.

## Add a receipt

- **No code:** fill in [the receipt form](https://github.com/opposablemeaning/vote/issues/new?template=new-receipt.yml). You need a free GitHub account.
- **Several at once, or from an AI agent:** put them in [the JSON format](CONTRIBUTING.md#the-format), using [the prompt for agents](CONTRIBUTING.md#using-an-ai-agent) if you work with one. Check the file with `node scripts/receipts.mjs check your-file.json`, then paste it into [the JSON form](https://github.com/opposablemeaning/vote/issues/new?template=receipts-json.yml) or open a pull request that adds it to [`submissions/`](submissions/).
- **Found a mistake?** Every receipt on the page has a "correct this" link. Corrections are as welcome as additions.

[CONTRIBUTING.md](CONTRIBUTING.md) has the rules, every field, every topic and label, and the agent prompt. The bar is the source, not the outrage.

## The data

| Path | What |
|---|---|
| `data/receipts.json` | Every receipt, plus the topics, the playbook, the scoreboard and the voting facts. Published at [opposablemeaning.com/vote/receipts.json](https://opposablemeaning.com/vote/receipts.json) |
| `docs/vote/receipt.schema.json` | The submission format as JSON Schema. Published at [opposablemeaning.com/vote/receipt.schema.json](https://opposablemeaning.com/vote/receipt.schema.json) |
| `scripts/receipts.mjs` | Checks receipts and submissions (`check`) and merges a submission into the data (`add`) |
| `scripts/build-site.mjs` | Builds the page into `docs/` (Cloudflare Pages runs it on every push) and refreshes the generated tables in CONTRIBUTING.md and the topic list in the receipt form |
| `submissions/` | Receipts from pull requests, waiting to be merged |
| `brand/` | The Opposable Meaning logo, profile pictures, banner and site icons, built by `scripts/build-brand.mjs` |

## The video

VOTE. THEM. OUT. is also [a video for the midterms](https://www.youtube.com/watch?v=HUumiZCCYDo), built from the same data: every claim on screen is a receipt here. Paused on an EXHIBIT number? The page lists every exhibit, in order.

| Path | What |
|---|---|
| `data/hero.exhibits.json` | EXHIBIT number → source, in on-screen order (written by the video build) |
| `templates/hero.html` | The video: an HTML + GSAP composition rendered with [HyperFrames](https://www.npmjs.com/package/hyperframes) |
| `scripts/build-hero.mjs` | Lays the receipts out on a 135 BPM beat grid; writes the composition and the audio cue sheet |
| `scripts/render_track1b_master.py` | Builds the soundtrack: synthesized music (`track_engines.py`), sound effects (`sfx_organic.py`, synthesis plus CC0 one-shots), the voice clips, ducking and the master |
| `scripts/sfx.py`, `music.py`, `kits.py`, `mix.py` | The earlier synthesized sound set; `mix.py` still builds the Shorts' soundtracks |
| `scripts/ccc_dots.py` | No Kings protest locations from the Crowd Counting Consortium dataset |

```sh
npm install                       # map data (us-atlas, topojson-client, d3-geo)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
node scripts/build-hero.mjs --site-live          # composition + cue sheet (add --after-oct17 after Oct 17)
.venv/bin/python scripts/render_track1b_master.py  # soundtrack -> hero/assets/audio/mix.wav
node scripts/build-site.mjs                        # the page -> docs/
cd hero && npx hyperframes@0.8.143 render --quality looks --output ../out/hero.mp4
```

The video build also expects media that isn't in this repo: two Trump audio clips in `assets/clips/` (used under fair use for commentary), and the CC0 field recordings and drum samples listed in `assets/audio/CREDITS.md`. Without them, the mix skips those clips with a warning.

## License

- Code: [MIT](LICENSE).
- Receipts data (`data/receipts.json`, `docs/vote/receipts.json`): [CC BY 4.0](LICENSE-DATA.md).
- Fonts: SIL Open Font License (Anton, Inter, JetBrains Mono) and Apache 2.0 (Special Elite). License texts are in `assets/fonts/`.
- Protest location data: Crowd Counting Consortium (Harvard Ash Center / UConn), CC0.
- Sound: synthesized from scratch, plus CC0 recordings and samples credited in `assets/audio/CREDITS.md`.
- The Opposable Meaning name and logo (`brand/`) are not covered by these licenses.
