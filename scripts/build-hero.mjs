// Builds hero/index.html + data/hero.cues.json from data/receipts.json.
// One clock: everything sits on a 135 BPM grid (positions are in beats), so the
// visuals and the mixed audio (scripts/mix.py reads the cues) land on the same frames.
//
//   node scripts/build-hero.mjs            full hero cut
//   node scripts/build-hero.mjs --proto    cold open + 2 beats (old prototype)
//   node scripts/build-hero.mjs --after-oct17   same cut without the dated No Kings Oct 17 panel

import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { feature, mesh } from "topojson-client";
import { geoPath, geoAlbersUsa, geoCentroid } from "d3-geo";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const HERO = join(ROOT, "hero");
const data = JSON.parse(readFileSync(join(ROOT, "data/receipts.json"), "utf8"));
const PROTO = process.argv.includes("--proto");
const AFTER17 = process.argv.includes("--after-oct17");
// receipts site (Cloudflare Pages); shown on the end card only once it is actually live
const SITE_URL = "opposablemeaning.com/vote";
const SITE_LIVE = process.argv.includes("--site-live");

const BPM = 135;
const BEAT = 60 / BPM;
const sec = (beats) => +(beats * BEAT).toFixed(4);

const byId = Object.fromEntries(data.receipts.map((r) => [r.id, r]));
const wordOf = Object.fromEntries(data.beats.map((x) => [x.id, x.word]));
// `short` is an on-screen caption for receipts whose full caption (kept for the site) is too long for a card
const card = (r) => ({ caption: r.short || r.caption, outlet: r.outlet, date: r.date, status: r.status, win: !!r.win });

const vis = [];
const cues = [];
const musicSegs = [];
const silence = [];
let exhibit = 0;

const V = (kind, atBeat, props = {}) => vis.push({ kind, t: sec(atBeat), ...props });
const S = (atBeat, name, gain = 1) => cues.push({ t: sec(atBeat), sfx: name, gain });
const CLIP = (atBeat, file, gain = 1, opts = {}) => cues.push({ t: sec(atBeat), clip: file, gain, ...opts });
const M = (atBeat, section, untilBeat, gain = 1) => musicSegs.push({ at: sec(atBeat), section, until: sec(untilBeat), gain });
const slap = (k) => ["card_slap_a", "card_slap_b", "card_slap_c"][k % 3];
// every EXHIBIT number on screen maps to its source (data/hero.exhibits.json -> receipts site)
const exhibits = [];
const nextExhibit = (src = {}) => {
  exhibit += 1;
  exhibits.push({ n: exhibit, id: src.id || null, caption: src.short || src.caption || src.text, outlet: src.outlet || null, date: src.date || null, url: src.url || null, status: src.status || null, also: src.also || null });
  return exhibit;
};

// ---------------------------------------------------------------- A. cold open
// His words, burned in as he says them. Word onsets (s, clip-relative) come from
// whisper-cli word timestamps refined against the clip's energy envelope.
let B = 0;
const COLD_AT = 0.25; // beats
const COLD_LEN = 4.877; // s, assets/clips/trump-cold-open.wav
const coldWords = [
  [0, "IT'LL", 0.04], [0, "BE", 0.28], [0, "FIXED.", 0.56],
  [0, "IT'LL", 1.16], [0, "BE", 1.38], [0, "FINE.", 1.55],
  [1, "YOU", 2.5], [1, "WON'T", 2.68], [1, "HAVE", 3.0], [1, "TO", 3.1], [1, "VOTE", 3.18], [1, "ANYMORE,", 3.48],
  [2, "MY", 3.86], [2, "BEAUTIFUL", 4.06], [2, "CHRISTIANS.", 4.44],
];
const watchAt = Math.ceil((COLD_LEN + sec(COLD_AT)) / BEAT); // first beat after he finishes
V("coldline", 0, {
  words: coldWords.map(([line, text, t]) => ({ line, text, t: +(sec(COLD_AT) + t).toFixed(3), red: text === "VOTE" || text === "ANYMORE," })),
  redAt: +(sec(COLD_AT) + 3.48).toFixed(3),
  attr: "Donald Trump · July 26, 2024 · Turning Point Action Believers' Summit",
  end: sec(watchAt),
});
S(0, "subdrop", 0.6);
for (let k = 0; k < watchAt; k += 2) S(k, "heartbeat", 0.45 + 0.03 * k);
CLIP(COLD_AT, "assets/clips/trump-cold-open.wav", 1.0);
S(watchAt - 1.6, "whoosh_up", 0.5);
V("slam", watchAt, { lines: [{ text: "WATCH US.", size: 300, color: "red" }], hold: sec(4) });
S(watchAt, "impact_hot", 1.0);
S(watchAt, "glitch", 0.35);
B = watchAt + 4;

// ---------------------------------------------------------------- B. act 1: the case against
// On-screen cards per word, in landing order. Not fixed at 4: a word gets as many cards as it
// has strong receipts (5-6 switch to a 3-across grid) and its segment runs longer. A list of
// lists is pages: the cards clear and the next page lands under the same word.
const HERO_PICKS = {
  corruption: ["c2", "c3", "c6", "c5", "c4", "i1"],
  tax: ["t1", "t2", "t5", "g21", "t3", "t4"],
  cruelty: ["x1", "x2", "x3", "x4", "x5"],
  war: [["w1", "w2", "w3"], ["w4", "w10", "w11", "w7", "w6"]],
  // the finding and the crimes; then our money, their leverage, and what they do with it
  genocide: [["gz1", "gz5", "gz2", "gz3"], ["gz7", "gz6", "gz11", "gz14", "gz15", "gz20"]],
  troops: ["m4", "m5", "m6", "m7"],
  women: ["f1", "f2", "f3", "f4"],
  healthcare: ["hc1", "hc3", "b1", "hc6", "b2", "hc9"],
  epstein: ["ep5", "ep2", "ep4", "ep6", "e3", "ep12"],
};
// the overload wall: mostly what they cost YOU (it lands on "IS A VOTE AGAINST: YOU.")
const WALL = [
  "si1", "si4", "si6", "si9", "a1", "si2", "si5", "hc7", "si12", "si7", "m1", "si3", "hc2",
  "si10", "rv1", "e1", "si11", "u3", "si8", "d1", "g2", "rv3", "hc8", "g13", "hc10", "i2",
  "gz17", "gz18", "gz19",
];
const ACT1 = PROTO ? ["corruption", "tax"] : Object.keys(HERO_PICKS);
const act1Start = B;
V("header", B, { text: "A VOTE FOR REPUBLICANS IS A VOTE FOR:" });
V("counter", B, {});
S(B, "stamp", 0.7);
let s = B + 2;
ACT1.forEach((beatId, i) => {
  const escalate = Math.min(1, i / Math.max(1, ACT1.length - 1));
  const pages = Array.isArray(HERO_PICKS[beatId][0]) ? HERO_PICKS[beatId] : [HERO_PICKS[beatId]];
  S(s - 1, "spin", 0.45);
  V("reel", s - 1, { word: wordOf[beatId], landAt: sec(s) });
  S(s, i > 4 ? "impact_hot" : i > 1 ? "impact_mid" : "impact", 0.95);
  S(s, "kachunk", 0.4);
  if (beatId === "corruption") S(s + 0.5, "register", 0.35);
  let p0 = s;
  pages.forEach((picks, pi) => {
    const n = picks.length;
    const first = 1.0;
    const gap = 1.0;
    const dur = Math.max(6, 2 * Math.ceil((first + (n - 1) * gap + 2.5) / 2));
    picks.forEach((rid, k) => {
      if (!byId[rid]) throw new Error(`unknown receipt ${rid}`);
      const at = p0 + first + k * gap;
      V("card", at, { slot: k, of: n, exhibit: nextExhibit(byId[rid]), r: card(byId[rid]) });
      S(at, slap(k), 0.75);
    });
    V("clear", p0 + dur - 0.5);
    S(p0 + dur - 0.5, "whoosh_down", 0.35);
    p0 += dur;
  });
  s = p0;
});
B = s;
M(act1Start, "groove", Math.min(B, act1Start + 16));
if (B > act1Start + 16) M(act1Start + 16, "drive", B);

if (!PROTO) {
  // ---------------------------------------------------------------- C. overload: ALL OF THE ABOVE
  const heroSet = new Set(Object.values(HERO_PICKS).flat(2));
  const wall = WALL.map((id) => byId[id]);
  wall.forEach((r, k) => {
    if (!r || heroSet.has(r.id)) throw new Error(`wall card ${WALL[k]}: missing or already a hero card`);
  });
  const allWords = data.beats.filter((x) => x.spin !== false).map((x) => x.word);
  V("overload", B, {
    words: allWords,
    landAt: sec(B + 8),
    cards: wall.map((r, k) => ({ t: sec(B + 0.25 + k * (7.4 / wall.length)), exhibit: nextExhibit(r), r: card(r) })),
  });
  wall.forEach((_, k) => S(B + 0.25 + k * (7.4 / wall.length), slap(k), 0.45));
  S(B, "spin_long", 0.5);
  S(B, "riser", 0.45);
  S(B + 4, "static_wall", 0.3);
  M(B, "frenzy", B + 8);
  B += 8;
  S(B, "kachunk", 0.9);
  S(B, "impact_hot", 0.8);

  // the turn: FOR -> AGAINST: YOU. No music here; the hit rings out (no hard cut), the
  // header glitches, the reel spins once more and lands on the viewer.
  const againstAt = B + 1.5;
  const youAt = B + 3;
  V("against", againstAt, {
    text: "A VOTE FOR REPUBLICANS IS A VOTE ",
    word: "AGAINST:",
    you: "YOU.",
    spinAt: sec(B + 2),
    landAt: sec(youAt),
  });
  S(againstAt, "glitch", 0.7);
  S(againstAt, "whoosh_down", 0.45);
  S(B + 2, "spin", 0.5);
  S(youAt, "impact_hot", 1.0);
  S(youAt, "impact", 0.8);
  S(youAt, "subdrop", 0.8);
  S(youAt, "kachunk", 0.5);
  S(youAt + 0.05, "boom_tail", 0.75);
  V("act1end", youAt + 4.8);
  B = youAt + 5;

  // ---------------------------------------------------------------- D. every accusation is a confession
  V("slam", B, {
    lines: [
      { text: "EVERY ACCUSATION", size: 170, color: "white" },
      { text: "IS A CONFESSION.", size: 190, color: "red" },
    ],
    stagger: 0.22,
    hold: sec(4),
  });
  S(B, "impact_hot", 1.0);
  S(B + 0.5, "impact_mid", 0.7);
  M(B, "drone", B + 4);
  B += 4;
  const flipsStart = B;
  V("seghead", B, { text: "EVERY ACCUSATION IS A CONFESSION.", end: null, id: "confess" });
  const flipDur = [6, 6, 5, 5];
  let musicCut = null;
  data.confessions.forEach((c, i) => {
    const flipAt = B + (i < 2 ? 2.5 : 2);
    let dur = flipDur[i] ?? 6;
    let stampAt = flipAt + 0.6;
    let hl = [];
    if (c.did.clip) {
      // his own voice: the card holds while the whole line plays, then gets stamped.
      // 11,780 clip: the line runs 3.3s -> end (user-confirmed); onsets from whisper + energy.
      const from = c.did.clip_from ?? 0;
      const len = c.did.clip_len - from;
      const clipAt = flipAt + 0.5;
      CLIP(clipAt, c.did.clip, 1.0, { from, fade: 0.02 });
      hl = (c.did.hl || []).map((h) => ({ match: h.match, at: +(sec(clipAt) + h.at - from).toFixed(3) }));
      stampAt = Math.ceil(clipAt + len / BEAT);
      dur = Math.ceil(stampAt + 2 - B);
      musicCut = flipAt;
    }
    V("flip", B, {
      said: c.said,
      did: c.did,
      flipAt: sec(flipAt),
      stampAt: sec(stampAt),
      pushIn: !!c.did.clip,
      hl,
      end: sec(B + dur),
      ex1: nextExhibit({ ...c.said, id: c.id + ".said" }),
      ex2: nextExhibit({ ...c.did, id: c.id + ".did" }),
    });
    S(B, "whoosh_fast", 0.4);
    S(B, "card_slap_b", 0.7);
    S(flipAt, "card_flip", 0.9);
    S(stampAt, c.did.clip ? "impact_hot" : "impact_mid", c.did.clip ? 1.0 : 0.85);
    S(stampAt + 0.15, "stamp", c.did.clip ? 0.8 : 0.6);
    B += dur;
  });
  if (musicCut) {
    M(flipsStart, "drive", musicCut);
    M(musicCut, "drone", B, 0.8);
  } else M(flipsStart, "drive", B);
  V("segend", B, { id: "confess" });

  // bridge
  V("slam", B, {
    lines: [
      { text: "SO WHEN THEY SAY", size: 120, color: "white" },
      { text: "THIS ELECTION WILL BE RIGGED…", size: 120, color: "white" },
    ],
    stagger: 0.44,
    hold: sec(4),
  });
  S(B, "impact", 0.6);
  S(B + 1, "impact", 0.5);
  V("slam", B + 4, { lines: [{ text: "THAT'S NOT A WARNING.", size: 150, color: "white" }], hold: sec(2) });
  S(B + 4, "impact_mid", 0.85);
  V("slam", B + 6, { lines: [{ text: "IT'S A CONFESSION.", size: 200, color: "red" }], hold: sec(2) });
  S(B + 6, "impact_hot", 1.0);
  M(B, "drone", B + 8);
  B += 8;

  // ---------------------------------------------------------------- E. the playbook
  V("slam", B, {
    lines: [
      { text: "THEY CAN'T WIN THE VOTE.", size: 130, color: "white" },
      { text: "SO THEY'RE COMING FOR THE VOTERS.", size: 110, color: "red" },
    ],
    stagger: 0.44,
    hold: sec(4),
  });
  S(B, "impact_mid", 0.8);
  S(B + 1, "impact_hot", 0.9);
  M(B, "groove", B + 4);
  B += 4;
  const pbStart = B;
  V("seghead", B, { text: "THEIR PLAYBOOK", id: "playbook", typewriter: true });
  data.playbook.forEach((p, i) => {
    const dur = i < 2 ? 6 : 5;
    const counterAt = B + (i < 2 ? 2.75 : 2.25);
    const minis = p.receipts.slice(0, 3).map((r, k) => ({
      t: sec(B + 0.6 + k * 0.5),
      exhibit: nextExhibit(r),
      r: card(r),
    }));
    V("trick", B, { n: p.n, trick: p.trick, counter: p.counter, minis, counterAt: sec(counterAt), end: sec(B + dur) });
    S(B, "stamp", 0.8);
    S(B, "card_slap_a", 0.5);
    minis.forEach((_, k) => S(B + 0.6 + k * 0.5, slap(k + 1), 0.45));
    S(counterAt, "cell_slam", 0.95);
    S(counterAt, "impact_mid", 0.6);
    B += dur;
  });
  M(pbStart, "drive", B);
  V("segend", B, { id: "playbook" });

  // scoreboard: a few big wins that prove the closer (turnout wins); the full list is on the site
  const wins = data.scoreboard.filter((w) => w.hero);
  const winAt = (k) => B + 1 + k * 3;
  const items = wins.map((w, k) => ({
    big: w.big,
    label: w.label,
    src: [w.outlet, w.date].filter(Boolean).join(" · "),
    t: sec(winAt(k)),
    exhibit: nextExhibit({ caption: `${w.big}: ${w.label}`, outlet: w.outlet, date: w.date, url: w.url, also: w.also, status: "WIN" }),
  }));
  const sbLen = winAt(wins.length - 1) + 4 - B;
  V("scoreboard", B, { items, end: sec(B + sbLen) });
  S(B, "whoosh_up", 0.4);
  items.forEach((_, k) => {
    S(winAt(k), "impact_mid", 0.8);
    S(winAt(k), "win_ding", 0.45);
    S(winAt(k) + 0.1, "stamp", 0.5);
  });
  M(B, "anthem", B + sbLen, 0.8);
  B += sbLen;

  // closer
  V("slam", B, { lines: [{ text: "THEY'RE NOT AFRAID OF YOUR ANGER.", size: 118, color: "white" }], hold: sec(3) });
  S(B, "impact_mid", 0.85);
  V("slam", B + 3, { lines: [{ text: "THEY'RE AFRAID OF YOUR TURNOUT.", size: 126, color: "red" }], hold: sec(3) });
  S(B + 3, "impact_hot", 1.0);
  M(B, "anthem", B + 6, 0.9);
  B += 6;
  V("counterend", B);

  // ---------------------------------------------------------------- F. finale
  // The clock line slides to center in the silence; the alarm then shakes it apart.
  const silenceAt = B + 8;
  const alarmAt = silenceAt + 4;
  const sirenAt = alarmAt + 2;
  V("clock", B, { text: "THEY'RE COUNTING ON YOU TO SLEEP THROUGH THIS.", ticks: 8, slideAt: sec(silenceAt), end: sec(sirenAt) });
  for (let k = 0; k < 8; k++) {
    S(B + k, k % 2 ? "clock_tock" : "clock_tick", 0.55 + 0.04 * k);
    if (k % 2 === 0) S(B + k, "heartbeat", 0.35);
  }
  M(B, "drone", silenceAt, 0.5);
  silence.push([sec(silenceAt), sec(alarmAt)]);
  V("alarm", alarmAt, { end: sec(sirenAt) });
  S(alarmAt, "alarm_morph", 0.9);
  S(sirenAt - 0.1, "siren_long", 0.45);
  S(sirenAt + 1.35, "crowd_swell", 0.18);
  // the next No Kings day is dated: `--after-oct17` builds the cut without it
  const next = AFTER17 ? null : data.finale.next_action?.on_screen;
  const nextAt = sirenAt + 8;
  const surgeAt = sirenAt + (next ? 17 : 10);
  const reelsAt = surgeAt + 4;
  const marchAt = sirenAt + 4;
  for (let k = 0; k < surgeAt + 2 - marchAt; k++) {
    S(marchAt + k, "crowd_stomp", 0.6);
    if (k % 2 === 1) S(marchAt + k, "crowd_clap", 0.4);
  }
  M(marchAt, "anthem", surgeAt + 2, 0.45);
  const mapData = buildMap();
  const stats = existsSync(join(ROOT, "data/map-stats.json")) ? JSON.parse(readFileSync(join(ROOT, "data/map-stats.json"), "utf8")) : null;
  const evRounded = stats ? Math.floor(stats.events_total / 100) * 100 : null;
  const evDays = stats ? Object.keys(stats.events_by_day).length : null;
  const sirenLines = [
    { at: sec(sirenAt + 2), text: "NO KINGS.", cls: "big" },
    { at: sec(sirenAt + 4), text: stats ? `${evDays} DAYS. ${evRounded.toLocaleString("en-US")}+ PROTESTS. ALL 50 STATES.` : "[PROTEST COUNT]", cls: "mid" },
    { at: sec(sirenAt + 6), text: "AMONG THE LARGEST PROTESTS IN AMERICAN HISTORY.", cls: "small" },
    { at: sec(surgeAt), text: "NOW TAKE IT TO THE BALLOT BOX.", cls: "mid", center: true, color: "#ffffff" },
  ];
  V("siren", sirenAt, {
    end: sec(reelsAt),
    surgeAt: sec(surgeAt),
    map: mapData,
    lines: sirenLines,
    next: next ? { ...next, at: sec(nextAt), urlAt: sec(nextAt + 2), noteAt: sec(nextAt + 3) } : null,
    source: "Protest locations: Crowd Counting Consortium (Harvard/UConn), No Kings days 6/14/25, 10/18/25, 3/28/26 · CC0",
  });
  if (next) {
    S(nextAt, "impact_hot", 0.9);
    S(nextAt, "stamp", 0.6);
    S(nextAt + 2, "impact_mid", 0.7);
  }
  S(sirenAt + 2, "impact_mid", 0.6);
  S(sirenAt + 4, "impact", 0.5);
  S(surgeAt, "whoosh_up", 0.6);
  S(surgeAt, "riser", 0.4);
  // real crowd (CC0 870537): the first "No kings!" (46.6s in the recording) lands on the NO KINGS. slam;
  // "This is what democracy looks like!" (55s+) follows. Fades cleanly before slot reels at 2:05.2, removing all traffic honks.
  const chantLead = 0.15;
  CLIP(sirenAt + 2 - chantLead / BEAT, "assets/audio/cc0/no-kings-chants-870537.wav", 1.02, { from: 46.6 - chantLead, dur: 8.5, fade: 0.75, duck: 0.9, eq: "presence", carve: 0.85 });
  const lands = [reelsAt + 2, reelsAt + 3, reelsAt + 4];
  V("reels", reelsAt, { words: ["VOTE.", "THEM.", "OUT."], lands: lands.map(sec), end: sec(reelsAt + 7) });
  S(reelsAt, "spin_reels", 0.5);
  lands.forEach((l, i) => {
    S(l, "impact", 1.0);
    S(l, ["impact_mid", "impact_mid", "impact_hot"][i], 0.9);
    S(l, "kachunk", 0.4);
  });
  S(lands[2] + 0.05, "boom_tail", 0.9);
  S(lands[2] + 0.2, "crowd_tail", 0.5);
  const END_BEATS = 22; // end card hold: long enough to read, and for YouTube's end-screen elements (5 s minimum)
  const videoEnd = reelsAt + 7 + 4 + END_BEATS;
  CLIP(lands[2] + 0.15, "assets/audio/cc0/crowd-cheers-870542.wav", 0.6, { from: 2.0, dur: sec(videoEnd - lands[2] - 0.15), fade: 0.05, fade_out: 4.0, duck: false });
  // (No music during slot reels: lets VOTE. THEM. OUT. impacts, kachunks, and crowd cheers land with full dynamic clarity)
  B = reelsAt + 7;

  // callback: his words, stamped
  V("callback", B, {
    quote: "“You won't have to vote anymore.”",
    attr: "Donald Trump · July 26, 2024",
    stampAt: sec(B + 1),
    stamp: "WATCH US.",
    end: sec(B + 4),
  });
  S(B, "card_slap_a", 0.7);
  S(B + 1, "impact_hot", 1.0);
  S(B + 1, "stamp", 0.8);
  B += 4;

  V("endcard", B, {
    plan: "PLAN WHEN AND WHERE TO VOTE — NOW.",
    friends: "BRING FRIENDS.",
    site: SITE_LIVE ? SITE_URL : null,
    end: null,
  });
  S(B, "impact", 0.7);
  M(B, "outro", B + END_BEATS, 0.35);
  B += END_BEATS;
}

const duration = +sec(B + (PROTO ? 2 : 0)).toFixed(3);

// ---------------------------------------------------------------- map (us-atlas, Albers USA 975x610)
function buildMap() {
  const states = JSON.parse(readFileSync(join(ROOT, "node_modules/us-atlas/states-albers-10m.json"), "utf8"));
  const counties = JSON.parse(readFileSync(join(ROOT, "node_modules/us-atlas/counties-albers-10m.json"), "utf8"));
  const path = geoPath();
  const nation = path(feature(states, states.objects.nation));
  const borders = path(mesh(states, states.objects.states, (a, b) => a !== b));
  let dots, placeholder;
  const dotsFile = join(ROOT, "data/map-dots.json");
  if (existsSync(dotsFile)) {
    // real event locations (Crowd Counting Consortium, CC0); territories fall outside Albers USA
    const proj = geoAlbersUsa().scale(1300).translate([487.5, 305]);
    dots = JSON.parse(readFileSync(dotsFile, "utf8"))
      .map((d) => proj([d.lon, d.lat]))
      .filter(Boolean);
    placeholder = false;
  } else {
    // DRAFT ONLY: county centroids (pre-projected). Replace with real event locations.
    dots = feature(counties, counties.objects.counties).features.map((f) => path.centroid(f)).filter((p) => p.every(Number.isFinite));
    placeholder = true;
  }
  // Deterministic, accelerating ignition: shuffle with a seeded PRNG, then split into
  // groups whose start times bunch toward the end (density ~ t^0.8).
  let seed = 4242;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const pts = dots.map((p) => [+p[0].toFixed(1), +p[1].toFixed(1)]);
  for (let i = pts.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [pts[i], pts[j]] = [pts[j], pts[i]];
  }
  const G = 56;
  const groups = Array.from({ length: G }, (_, g) => pts.slice(Math.floor((g * pts.length) / G), Math.floor(((g + 1) * pts.length) / G)));
  const groupAt = groups.map((_, g) => +Math.pow((g + 1) / G, 0.55).toFixed(4));
  const flyers = pts.filter((_, i) => i % 18 === 0).slice(0, 420);
  return { nation, borders, groups, groupAt, flyers, placeholder, count: pts.length };
}

// ---------------------------------------------------------------- write outputs
mkdirSync(join(ROOT, "data"), { recursive: true });
writeFileSync(join(ROOT, "data/hero.exhibits.json"), JSON.stringify(exhibits, null, 1));
writeFileSync(
  join(ROOT, "data/hero.cues.json"),
  JSON.stringify({ bpm: BPM, duration, music: musicSegs, cues, silence }, null, 1),
);
mkdirSync(join(HERO, "assets/fonts"), { recursive: true });
cpSync(join(ROOT, "assets/fonts"), join(HERO, "assets/fonts"), { recursive: true });
if (existsSync(join(ROOT, "assets/clips"))) cpSync(join(ROOT, "assets/clips"), join(HERO, "assets/clips"), { recursive: true });

const tpl = readFileSync(join(ROOT, "templates/hero.html"), "utf8");
const html = tpl
  .replaceAll("__DURATION__", String(duration))
  .replace("__VIS__", JSON.stringify(vis))
  .replace("__BEAT__", String(BEAT));
writeFileSync(join(HERO, "index.html"), html);
console.log(`hero: ${duration}s (${(duration / 60).toFixed(2)} min), ${vis.length} visual events, ${cues.length} audio cues, ${exhibit} exhibits`);
