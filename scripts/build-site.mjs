// Builds the public receipts page from data/receipts.json and data/hero.exhibits.json
// (run build-hero.mjs first so EXHIBIT numbers match the video). docs/ is the Cloudflare Pages
// build output; the page lives at /vote/ so the domain root stays free.
//
//   node scripts/build-site.mjs   ->  docs/vote/index.html (+ fonts, receipts.json)
//                                     docs/_redirects, docs/_headers, docs/index.html (root -> /vote/)

import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DOCS = join(ROOT, "docs");
const OUT = join(DOCS, "vote");
const SITE = "https://opposablemeaning.com/vote/";
const REPO = "https://github.com/opposablemeaning/vote";
const data = JSON.parse(readFileSync(join(ROOT, "data/receipts.json"), "utf8"));
const exhibitsFile = join(ROOT, "data/hero.exhibits.json");
const exhibits = existsSync(exhibitsFile) ? JSON.parse(readFileSync(exhibitsFile, "utf8")) : [];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };
const shown = (r) => r && r.url && !/VERIFY/i.test(`${r.outlet} ${r.status}`);
const badge = (status, win) => {
  const st = win ? "WIN" : status || "SOURCE";
  return `<span class="st st-${esc(st.split(" ")[0])}">${esc(st)}</span>`;
};
const also = (r) => [].concat(r.also || []).filter(Boolean).map((u) => ` · <a href="${esc(u)}" rel="noopener">also: ${esc(host(u))}</a>`).join("");
const item = (r, ex = null) => `
      <li class="rc"${ex ? ` id="ex${ex}"` : ""}>
        ${ex ? `<span class="exn">EXHIBIT ${String(ex).padStart(2, "0")}</span>` : ""}${badge(r.status, r.win)}
        <p class="cap">${esc(r.caption || r.text)}</p>
        <p class="src"><a href="${esc(r.url)}" rel="noopener">${esc(r.outlet || host(r.url))}${r.date ? " · " + esc(r.date) : ""}</a>${also(r)}</p>
        ${r.note ? `<p class="note">${esc(r.note)}</p>` : ""}
      </li>`;

// exhibits in the order they appear on screen
const exhibitList = exhibits
  .filter((x) => x.url)
  .map((x) => item(x, x.n))
  .join("");

// every receipt by topic, in the video's order
const byBeat = data.beats
  .map((b) => {
    const rs = data.receipts.filter((r) => r.beat === b.id && shown(r));
    if (!rs.length) return "";
    const head = b.id === "you" ? "A VOTE FOR REPUBLICANS IS A VOTE AGAINST: <b>YOU</b>" : `A VOTE FOR REPUBLICANS IS A VOTE FOR: <b>${esc(b.word)}</b>`;
    return `
    <section class="beat" id="${esc(b.id)}" data-search>
      <h3>${head}</h3>
      <ul>${rs.map((r) => item(r)).join("")}
      </ul>
    </section>`;
  })
  .join("");

const confessions = data.confessions
  .map((c) => `
      <div class="pair" data-search>
        <div><span class="lbl">THEY SAID</span>${item(c.said).replace(/<\/?li[^>]*>/g, "")}</div>
        <div><span class="lbl red">THEY DID</span>${item(c.did).replace(/<\/?li[^>]*>/g, "")}</div>
      </div>`)
  .join("");

const playbook = data.playbook
  .map((p) => `
      <div class="trick" data-search>
        <p class="tn">TRICK #${p.n}: ${esc(p.trick)}</p>
        <p class="counter">${esc(p.counter)}</p>
        <ul>${p.receipts.filter(shown).map((r) => item(r)).join("")}</ul>
      </div>`)
  .join("");

const scoreboard = data.scoreboard
  .map((w) => `<li><span>${esc(w.text)}</span><span><a href="${esc(w.url)}" rel="noopener">${esc(w.result)} ✓</a>${also(w)}</span></li>`)
  .join("");

const f = data.facts;
const next = data.finale?.next_action;
const total = data.receipts.filter(shown).length;

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VOTE. THEM. OUT. · The Receipts</title>
<meta name="description" content="Every claim in VOTE. THEM. OUT., with its source. Election Day is Tuesday, Nov 3. Check your registration at vote.org.">
<link rel="canonical" href="${SITE}">
<meta property="og:type" content="website">
<meta property="og:url" content="${SITE}">
<meta property="og:title" content="VOTE. THEM. OUT. · The Receipts">
<meta property="og:description" content="Every claim in the video, with its source. Election Day is Tuesday, Nov 3. Check your registration at vote.org.">
<meta property="og:image" content="${SITE}og.jpg">
<meta name="twitter:card" content="summary_large_image">
<style>
  @font-face { font-family: "Anton"; src: url("/vote/fonts/Anton-Regular.ttf"); font-display: swap; }
  @font-face { font-family: "Inter"; src: url("/vote/fonts/Inter.ttf"); font-weight: 100 900; font-display: swap; }
  :root { --ink: #0b0b0c; --panel: #151518; --line: #2a2a30; --text: #f5f5f4; --muted: #a8a29e; --red: #e3122b; --tag: #ffd400; --win: #22c55e; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--ink); color: var(--text); font: 17px/1.5 "Inter", system-ui, sans-serif; }
  a { color: #fde68a; }
  .wrap { max-width: 980px; margin: 0 auto; padding: 0 16px; }
  header.wrap { padding-top: 40px; padding-bottom: 24px; text-align: center; }
  h1 { font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: clamp(56px, 12vw, 120px); line-height: 0.95; margin: 0; letter-spacing: 0.01em; }
  h1 span { color: var(--red); }
  .sub { color: var(--muted); margin: 10px 0 26px; font-weight: 700; letter-spacing: 0.04em; }
  .cta { display: inline-block; background: var(--tag); color: var(--ink); text-decoration: none; font-family: "Anton", Impact, sans-serif; font-size: clamp(28px, 6vw, 44px); padding: 12px 28px; border-radius: 6px; }
  .cta small { display: block; font-family: "Inter", sans-serif; font-weight: 800; font-size: 14px; letter-spacing: 0.08em; }
  .day { font-family: "Anton", Impact, sans-serif; color: var(--red); font-size: clamp(30px, 7vw, 56px); margin: 18px 0 0; }
  .nk { border: 4px solid var(--red); padding: 14px 18px; margin: 24px auto 0; max-width: 680px; background: var(--panel); }
  .nk b { font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: 26px; letter-spacing: 0.02em; }
  .nk p { margin: 6px 0 0; color: var(--muted); font-size: 15px; }
  nav { position: sticky; top: 0; z-index: 2; background: rgba(11,11,12,0.95); border-bottom: 1px solid var(--line); padding: 10px 0; }
  nav .wrap { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
  nav a { color: var(--text); text-decoration: none; font-weight: 800; font-size: 14px; letter-spacing: 0.04em; }
  #q { flex: 1 1 220px; min-width: 0; background: var(--panel); color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; font: inherit; }
  h2 { font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: clamp(34px, 7vw, 54px); margin: 48px 0 6px; line-height: 1; }
  h2 + p { color: var(--muted); margin: 0 0 18px; }
  h3 { font-size: 17px; letter-spacing: 0.06em; font-weight: 900; margin: 30px 0 10px; color: var(--muted); }
  h3 b { color: var(--red); font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: 26px; letter-spacing: 0.02em; }
  ul { list-style: none; margin: 0; padding: 0; }
  .rc { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; margin: 0 0 10px; scroll-margin-top: 70px; }
  .rc:target { outline: 3px solid var(--tag); }
  .exn { display: inline-block; background: var(--tag); color: var(--ink); font-weight: 900; font-size: 12px; letter-spacing: 0.06em; padding: 2px 8px; margin-right: 8px; }
  .st { display: inline-block; font-weight: 900; font-size: 11px; letter-spacing: 0.1em; padding: 1px 7px; border: 2px solid currentColor; border-radius: 3px; }
  .st-QUOTE { color: #f59e0b; } .st-COURT { color: #60a5fa; } .st-REPORTED { color: #d6d3d1; } .st-DATA { color: #2dd4bf; }
  .st-ESTIMATE { color: #c084fc; } .st-OFFICIAL { color: #4ade80; } .st-PROPOSED { color: #fb923c; } .st-LAW { color: #93c5fd; } .st-WIN { color: var(--win); }
  .cap { font-weight: 800; font-size: 19px; line-height: 1.3; margin: 8px 0 6px; }
  .src { margin: 0; font-size: 14px; color: var(--muted); overflow-wrap: anywhere; }
  .note { margin: 8px 0 0; font-size: 14px; color: var(--muted); border-left: 3px solid var(--line); padding-left: 10px; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
  .pair > div { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }
  .lbl { display: inline-block; background: var(--text); color: var(--ink); font-weight: 900; font-size: 12px; letter-spacing: 0.12em; padding: 2px 8px; margin-bottom: 8px; }
  .lbl.red { background: var(--red); color: #fff; }
  .trick { margin-bottom: 18px; }
  .tn { font-weight: 900; margin: 0; color: var(--muted); letter-spacing: 0.04em; }
  .counter { font-family: "Anton", Impact, sans-serif; font-size: 28px; color: var(--red); margin: 2px 0 10px; line-height: 1.1; }
  .sb li { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding: 10px 0; font-weight: 800; }
  .sb a { color: var(--win); text-decoration: none; white-space: nowrap; }
  .rights li { background: var(--panel); border-left: 4px solid var(--tag); padding: 10px 14px; margin-bottom: 8px; }
  footer.wrap { color: var(--muted); font-size: 14px; border-top: 1px solid var(--line); margin-top: 60px; padding-top: 24px; padding-bottom: 60px; }
  .hide { display: none !important; }
  @media (max-width: 640px) { .pair { grid-template-columns: 1fr; } body { font-size: 16px; } .cap { font-size: 17px; } }
</style>
</head>
<body>
<header class="wrap">
  <h1>VOTE. THEM. <span>OUT.</span></h1>
  <p class="sub">THE RECEIPTS · ${total} SOURCED CLAIMS · ${exhibits.length} EXHIBITS IN THE VIDEO</p>
  <a class="cta" href="https://www.vote.org/am-i-registered-to-vote/" rel="noopener">VOTE.ORG<small>CHECK YOUR REGISTRATION TODAY</small></a>
  <p class="day">TUESDAY, NOV 3</p>
  ${next ? `<div class="nk" id="nk" data-until="2026-10-18">
    <b>SAT, OCT 17 · NO KINGS: VOTE EARLY</b>
    <p>Vote early where you can, or make your plan. Early voting dates vary by state: <a href="https://www.vote.org/early-voting-calendar/" rel="noopener">vote.org</a>. Events: <a href="${esc(next.source)}" rel="noopener">nokings.org</a></p>
  </div>` : ""}
</header>
<nav><div class="wrap">
  <a href="#exhibits">EXHIBITS</a><a href="#topics">BY TOPIC</a><a href="#confessions">CONFESSIONS</a><a href="#playbook">PLAYBOOK</a><a href="#rights">YOUR RIGHTS</a>
  <input id="q" type="search" placeholder="Search receipts (e.g. Medicaid, Epstein, tariffs)" aria-label="Search receipts">
</div></nav>
<main class="wrap">
  <h2 id="exhibits">EVERY EXHIBIT IN THE VIDEO</h2>
  <p>Paused on an EXHIBIT number? It's here, in order, with the source. Status labels say what kind of evidence each one is: QUOTE, COURT RULING, COURT ORDER, COURT FILING, OFFICIAL record, REPORTED by a news outlet, DATA, ESTIMATE, PROPOSED, LAW.</p>
  <ul data-search-list>${exhibitList}
  </ul>

  <h2 id="topics">EVERY RECEIPT, BY TOPIC</h2>
  <p>Including the ones that didn't fit in the video.</p>
  ${byBeat}

  <h2 id="confessions">EVERY ACCUSATION IS A CONFESSION</h2>
  <p>What they said, then what they did.</p>
  ${confessions}

  <h2 id="playbook">THEIR PLAYBOOK</h2>
  <p>How they try to keep you home, and what to do about it.</p>
  ${playbook}

  <h2>THE SCOREBOARD</h2>
  <p>When we show up, we win.</p>
  <ul class="sb">${scoreboard}</ul>

  <h2 id="rights">YOUR RIGHTS AT THE POLLS</h2>
  <p>Problems voting? Election Protection: <b>${esc(f.hotline.en)}</b> · en español <b>${esc(f.hotline.es)}</b> (<a href="${esc(f.hotline.source)}" rel="noopener">866ourvote.org</a>)</p>
  <ul class="rights">
    <li>${esc(f.in_line.text)} (<a href="${esc(f.in_line.source)}" rel="noopener">source</a>)</li>
    <li>${esc(f.provisional.text)} (<a href="${esc(f.provisional.source)}" rel="noopener">source</a>)</li>
    <li>${esc(f.intimidation.text)} (<a href="${esc(f.intimidation.source)}" rel="noopener">source</a>)</li>
    <li>Registration deadlines and voting rules differ by state. Check yours at <a href="https://www.vote.org" rel="noopener">vote.org</a> or <a href="https://www.canivote.org" rel="noopener">canivote.org</a>.</li>
  </ul>
</main>
<footer class="wrap">
  <p><b>Found an error or a better source?</b> This list is public and correctable: open an issue or pull request at <a href="${REPO}" rel="noopener">${REPO.replace("https://", "")}</a>. Every receipt needs a source and an honest status label.</p>
  <p>Data (receipts) CC BY 4.0 · code MIT. Protest map data: Crowd Counting Consortium (Harvard Ash Center / UConn), CC0. Sound: synthesized, plus CC0 field recordings and samples (credits in the repo).</p>
</footer>
<script>
  // hide the dated No Kings banner after Oct 17
  const nk = document.getElementById("nk");
  if (nk && new Date() >= new Date(nk.dataset.until + "T12:00:00Z")) nk.classList.add("hide");
  // live filter
  const q = document.getElementById("q");
  const items = [...document.querySelectorAll(".rc, .pair, .trick")];
  q.addEventListener("input", () => {
    const t = q.value.trim().toLowerCase();
    items.forEach((el) => el.classList.toggle("hide", !!t && !el.textContent.toLowerCase().includes(t)));
    document.querySelectorAll(".beat").forEach((s) => s.classList.toggle("hide", !!t && !s.querySelector(".rc:not(.hide)")));
  });
</script>
</body>
</html>
`;

mkdirSync(join(OUT, "fonts"), { recursive: true });
for (const font of ["Anton-Regular.ttf", "Anton-OFL.txt", "Inter.ttf", "Inter-OFL.txt"]) cpSync(join(ROOT, "assets/fonts", font), join(OUT, "fonts", font));
writeFileSync(join(OUT, "index.html"), html);
writeFileSync(join(OUT, "receipts.json"), JSON.stringify(data, null, 1));

// Cloudflare Pages: the root goes to the page (302: the root may get its own page later). No
// /vote -> /vote/ rule: if Pages matched it against /vote/ too, it would loop; asset paths are absolute.
writeFileSync(join(DOCS, "_redirects"), "/ /vote/ 302\n");
writeFileSync(join(DOCS, "_headers"), [
  "/vote/fonts/*",
  "  Cache-Control: public, max-age=31536000, immutable",
  "/*",
  "  X-Content-Type-Options: nosniff",
  "  Referrer-Policy: strict-origin-when-cross-origin",
  "",
].join("\n"));
// fallback for hosts that ignore _redirects (and GitHub Pages until it is switched off)
writeFileSync(join(DOCS, "index.html"), `<!doctype html><meta charset="utf-8"><title>VOTE. THEM. OUT.</title><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url=vote/"><link rel="canonical" href="${SITE}"><a href="vote/">The receipts</a>\n`);
writeFileSync(join(DOCS, ".nojekyll"), "");
console.log(`site: docs/vote/index.html (${total} receipts, ${exhibits.length} exhibits)`);
