// Builds a vertical Short from data/shorts/<id>.json on the same 135 BPM grid as the hero.
//
//   node scripts/build-short.mjs diesel   ->  shorts/diesel/index.html + data/short-diesel.cues.json
//   .venv/bin/python scripts/mix.py data/short-diesel.cues.json shorts/diesel/assets/audio/mix.wav
//
// Spec steps (each lasts `beats`): { slam, stagger, slamAt } big centered lines;
// { kicker } persistent top headline (HTML, <b> = red); { head } yellow lead-in line;
// { bigstat, label } giant number; { cards: [receipt ids], cardY }; { end } VOTE. THEM. OUT. card.
// `music` names a music.py section for the step.

import { readFileSync, writeFileSync, mkdirSync, cpSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const id = process.argv[2];
if (!id) throw new Error("usage: node scripts/build-short.mjs <id>");
const spec = JSON.parse(readFileSync(join(ROOT, "data/shorts", `${id}.json`), "utf8"));
const data = JSON.parse(readFileSync(join(ROOT, "data/receipts.json"), "utf8"));
const byId = Object.fromEntries(data.receipts.map((r) => [r.id, r]));
const OUT = join(ROOT, "shorts", id);
const SITE = process.argv.includes("--site-live") ? "opposablemeaning.com/vote" : null;

const BEAT = 60 / 135;
const sec = (b) => +(b * BEAT).toFixed(4);
const vis = [];
const cues = [];
const music = [];
const V = (kind, atBeat, props = {}) => vis.push({ kind, t: sec(atBeat), ...props });
const S = (atBeat, sfx, gain = 1) => cues.push({ t: sec(atBeat), sfx, gain });
const slap = (k) => ["card_slap_a", "card_slap_b", "card_slap_c"][k % 3];
let exhibit = 0;
let B = 0;
let kickerOn = null;

for (const st of spec.steps) {
  const len = st.beats ?? 6;
  const end = B + len;
  if (st.kicker) {
    V("kicker", B, { html: st.kicker });
    S(B, "whoosh_fast", 0.4);
    kickerOn = vis.at(-1);
    continue;
  }
  if (st.kickerOff && kickerOn) kickerOn.end = sec(B);
  if (st.music) music.push({ at: sec(B), section: st.music, until: sec(end), gain: st.music === "drone" ? 0.6 : 0.85 });
  if (st.head) {
    V("head", B, { text: st.head, end: sec(end - 0.25) });
    S(B, "whoosh_fast", 0.35);
  }
  if (st.slam) {
    const at = B + (st.slamAt ?? 0);
    V("slam", at, { lines: st.slam.map((l) => ({ ...l, color: l.color || "white" })), stagger: sec(st.stagger ?? 0), end: sec(end - 0.1) });
    st.slam.forEach((l, i) => {
      const t = at + (st.stagger ?? 0) * i;
      S(t, l.color === "red" ? "impact_hot" : "impact_mid", l.color === "red" ? 1.0 : 0.85);
      if (l.color === "red") S(t, "subdrop", 0.5);
    });
  }
  if (st.bigstat) {
    V("bigstat", B + 0.5, { text: st.bigstat, label: st.label, end: sec(end - 0.25) });
    S(B + 0.5, "impact_hot", 1.0);
    S(B + 0.5, "register", 0.5);
  }
  (st.cards || []).forEach((rid, k) => {
    const r = byId[rid];
    if (!r) throw new Error(`unknown receipt ${rid}`);
    const at = B + (st.bigstat ? 2.5 : 1) + k * 2;
    V("card", at, {
      exhibit: ++exhibit,
      r: { caption: r.short || r.caption, outlet: r.outlet, date: r.date, status: r.status },
      y: (st.cardY ?? 760) + k * 460,
      rot: k % 2 ? 1.5 : -1.5,
      end: sec(end - 0.35),
    });
    S(at, slap(k), 0.85);
    S(at + 0.25, "stamp", 0.5);
  });
  if (st.end) {
    if (kickerOn && !kickerOn.end) kickerOn.end = sec(B);
    const lands = [B + 1, B + 2, B + 3];
    V("endcard", B, { words: ["VOTE.", "THEM.", "OUT."], lands: lands.map(sec), orgAt: sec(B + 5), site: SITE });
    lands.forEach((l, i) => {
      S(l, "impact", 1.0);
      S(l, ["impact_mid", "impact_mid", "impact_hot"][i], 0.9);
    });
    S(lands[2] + 0.05, "boom_tail", 0.8);
    S(B + 5, "impact", 0.6);
  }
  B = end;
}

const duration = +sec(B).toFixed(3);
mkdirSync(join(OUT, "assets/fonts"), { recursive: true });
cpSync(join(ROOT, "assets/fonts"), join(OUT, "assets/fonts"), { recursive: true });
writeFileSync(join(ROOT, `data/short-${id}.cues.json`), JSON.stringify({ bpm: 135, duration, music, cues, silence: [] }, null, 1));
const tpl = readFileSync(join(ROOT, "templates/short.html"), "utf8");
writeFileSync(join(OUT, "index.html"), tpl.replaceAll("__DURATION__", String(duration)).replace("__VIS__", JSON.stringify(vis)));
console.log(`short ${id}: ${duration}s, ${vis.length} visual events, ${cues.length} cues, ${exhibit} exhibits`);
