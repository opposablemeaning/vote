// Builds the public page from data/receipts.json: how to vote, then every receipt by topic, the
// playbook and the scoreboard, then how to add a receipt and the video's exhibits. docs/ is the
// Cloudflare Pages output (Pages runs this on every push); the page lives at /vote/ so the domain
// root stays free. It also publishes the receipt format and refreshes the generated parts of the
// contributor docs, so run it after changing data/receipts.json and commit what it writes.
//
//   node scripts/build-site.mjs   ->  docs/vote/index.html (+ fonts, receipts.json, receipt.schema.json)
//                                     docs/_redirects, docs/_headers, docs/index.html (root -> /vote/)
//                                     docs/favicon.svg, favicon.ico, apple-touch-icon.png (from brand/)
//                                     CONTRIBUTING.md (label and topic tables)
//                                     .github/ISSUE_TEMPLATE/new-receipt.yml (topic list)

import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { SITE, REPO, LABELS, schema, labelTable, topicTable, receiptForm } from "./receipts.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DOCS = join(ROOT, "docs");
const OUT = join(DOCS, "vote");
const VIDEO = "https://www.youtube.com/watch?v=HUumiZCCYDo"; // the hero cut on YouTube
const CHANNEL = "https://www.youtube.com/@OpposableMeaning";
// the mark from brand/ (scripts/build-brand.mjs), cropped to its edges for inline use
const MARK = readFileSync(join(ROOT, "brand/mark-on-dark.svg"), "utf8").trim()
  .replace('viewBox="0 0 512 512"', 'viewBox="89 74 334 364" width="22" height="24" aria-hidden="true"');
const data = JSON.parse(readFileSync(join(ROOT, "data/receipts.json"), "utf8"));
const stats = JSON.parse(readFileSync(join(ROOT, "data/map-stats.json"), "utf8"));
const exhibitsFile = join(ROOT, "data/hero.exhibits.json");
const exhibits = existsSync(exhibitsFile) ? JSON.parse(readFileSync(exhibitsFile, "utf8")) : [];

const VOTE = {
  check: "https://www.vote.org/am-i-registered-to-vote/",
  register: "https://www.vote.org/register-to-vote/",
  polls: "https://www.vote.org/polling-place-locator/",
  early: "https://www.vote.org/early-voting-calendar/",
  mail: "https://www.vote.org/absentee-ballot/",
  id: "https://www.vote.org/voter-id-laws/",
  ballot: "https://www.vote411.org/ballot",
};
const FORM = {
  receipt: `${REPO}/issues/new?template=new-receipt.yml`,
  json: `${REPO}/issues/new?template=receipts-json.yml`,
  fix: (id) => `${REPO}/issues/new?template=correction.yml&title=${encodeURIComponent(`Correction: ${id}`)}&receipt=${encodeURIComponent(id)}`,
};
const GUIDE = `${REPO}/blob/main/CONTRIBUTING.md`;

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };
const shown = (r) => r && r.url && !/VERIFY/i.test(`${r.outlet} ${r.status}`);
// 866-OUR-VOTE -> tel:+18666878683
const dial = (n) => "+1" + n.replace(/[A-Z]/g, (c) => "22233344455566677778889999"[c.charCodeAt(0) - 65]).replace(/\D/g, "");
const tel = (n) => `<a class="tel" href="tel:${dial(n)}">${esc(n)}</a>`;
const badge = (status, win) => {
  const st = win ? "WIN" : status || "SOURCE";
  return `<span class="st st-${esc(st.split(" ")[0])}">${esc(st)}</span>`;
};
const also = (r) => [].concat(r.also || []).filter(Boolean).map((u) => ` · <a href="${esc(u)}" rel="noopener">also: ${esc(host(u))}</a>`).join("");
const item = (r, ex = null) => `
      <li class="rc"${ex ? ` id="ex${ex}"` : r.id ? ` id="r-${esc(r.id)}"` : ""}>
        ${ex ? `<span class="exn">EXHIBIT ${String(ex).padStart(2, "0")}</span>` : ""}${badge(r.status, r.win)}
        <p class="cap">${esc(r.caption || r.text)}</p>
        <p class="src"><a href="${esc(r.url)}" rel="noopener">${esc(r.outlet || host(r.url))}${r.date ? " · " + esc(r.date) : ""}</a>${also(r)}</p>
        ${[r.sub, r.note].filter(Boolean).map((t) => `<p class="note">${esc(t)}</p>`).join("")}
        ${r.id && !ex ? `<p class="rid"><a href="#r-${esc(r.id)}">#${esc(r.id)}</a> · <a href="${esc(FORM.fix(r.id))}" rel="noopener">correct this</a></p>` : ""}
      </li>`;

// every receipt, by topic
const topics = data.beats
  .map((b) => ({ b, rs: data.receipts.filter((r) => r.beat === b.id && shown(r)) }))
  .filter((t) => t.rs.length);
const chips = topics.map(({ b, rs }) => `<a href="#${esc(b.id)}">${esc(b.word)}<span>${rs.length}</span></a>`).join("");
const byTopic = topics
  .map(({ b, rs }) => `
    <section class="beat" id="${esc(b.id)}">
      <h3>${b.id === "you" ? "A VOTE FOR REPUBLICANS IS A VOTE AGAINST: <b>YOU</b>" : `A VOTE FOR REPUBLICANS IS A VOTE FOR: <b>${esc(b.word)}</b>`}</h3>
      <ul>${rs.map((r) => item(r)).join("")}
      </ul>
    </section>`)
  .join("");
const legend = [...LABELS, ["WIN", "They were stopped: blocked in court, voted down"]]
  .map(([s, m]) => `<li>${s === "WIN" ? badge(null, true) : badge(s)} ${esc(m)}</li>`)
  .join("");

const confessions = data.confessions
  .map((c) => `
      <div class="pair">
        <div><span class="lbl">THEY SAID</span>${item(c.said).replace(/<\/?li[^>]*>/g, "")}</div>
        <div><span class="lbl red">THEY DID</span>${item(c.did).replace(/<\/?li[^>]*>/g, "")}</div>
      </div>`)
  .join("");

const playbook = data.playbook
  .map((p) => `
      <div class="trick">
        <p class="tn">TRICK #${p.n}: ${esc(p.trick)}</p>
        <p class="counter">${esc(p.counter)}</p>
        <ul>${p.receipts.filter(shown).map((r) => item(r)).join("")}</ul>
      </div>`)
  .join("");

const scoreboard = data.scoreboard
  .map((w) => `<li><span>${esc(w.text)}</span><span><a href="${esc(w.url)}" rel="noopener">${esc(w.result)} ✓</a>${also(w)}</span></li>`)
  .join("");

// exhibits in the order they appear in the video
const exhibitList = exhibits.filter((x) => x.url).map((x) => item(x, x.n)).join("");

const quick = [
  [VOTE.register, "Register to vote"],
  [VOTE.polls, "Find your polling place"],
  [VOTE.early, "Early voting dates"],
  [VOTE.mail, "Vote by mail"],
  [VOTE.id, "ID rules in your state"],
  [VOTE.ballot, "See what's on your ballot"],
].map(([u, t]) => `<a href="${u}" rel="noopener">${t}</a>`).join("");

// No Kings: the Oct 17 early-voting day until it's over, then a standing line (the script picks)
const nk = data.finale?.next_action;
const protests = `${(Math.floor(stats.events_total / 100) * 100).toLocaleString("en-US")}+`;
const noKings = nk ? `
  <div class="nk" id="nk-before">
    <b>SAT, OCT 17 · NO KINGS: THE PROTEST IS THE VOTE</b>
    <p>No Kings' nationwide early-voting day. Early voting is open that day in some states, not all: <a href="${VOTE.early}" rel="noopener">check your dates</a>. Not open yet where you live? Make your plan and bring people on Nov 3. Events: <a href="${esc(nk.source)}" rel="noopener">nokings.org</a></p>
  </div>
  <div class="nk hide" id="nk-after">
    <b>NO KINGS: THE PROTEST IS THE VOTE</b>
    <p>${Object.keys(stats.events_by_day).length} No Kings days, ${protests} protests, all 50 states (<a href="${esc(data.finale.protest_source.url)}" rel="noopener">Crowd Counting Consortium</a>). Now the one that counts: <a href="${VOTE.early}" rel="noopener">vote early</a> where you can, or on Tuesday, Nov 3.</p>
  </div>` : "";

const f = data.facts;
const h = f.hotline;
const total = data.receipts.filter(shown).length;
const TITLE = "VOTE. THEM. OUT. · The case against Trump and the GOP";

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${TITLE}</title>
<meta name="description" content="${total} sourced receipts on Trump and the GOP: corruption, cruelty, war, healthcare, the Epstein files and more. Election Day is Tuesday, Nov 3. Check your registration at vote.org.">
<link rel="canonical" href="${SITE}">
<meta property="og:type" content="website">
<meta property="og:url" content="${SITE}">
<meta property="og:title" content="${TITLE}">
<meta property="og:description" content="${total} receipts, every one sourced. Election Day is Tuesday, Nov 3: check your registration at vote.org.">
<meta property="og:image" content="${SITE}og.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#0b0b0c">
<style>
  @font-face { font-family: "Anton"; src: url("/vote/fonts/Anton-Regular.ttf"); font-display: swap; }
  @font-face { font-family: "Inter"; src: url("/vote/fonts/Inter.ttf"); font-weight: 100 900; font-display: swap; }
  :root { --ink: #0b0b0c; --panel: #151518; --line: #2a2a30; --text: #f5f5f4; --muted: #a8a29e; --red: #e3122b; --tag: #ffd400; --win: #22c55e; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--ink); color: var(--text); font: 17px/1.5 "Inter", system-ui, sans-serif; }
  a { color: #fde68a; }
  .wrap { max-width: 980px; margin: 0 auto; padding: 0 16px; }
  header.wrap { padding-top: 40px; padding-bottom: 28px; text-align: center; }
  h1 { font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: clamp(56px, 12vw, 120px); line-height: 0.95; margin: 0; letter-spacing: 0.01em; }
  h1 span { color: var(--red); }
  .vote { max-width: 760px; margin: 30px auto 0; }
  .whenl { font-family: "Anton", Impact, sans-serif; font-size: clamp(26px, 5vw, 40px); letter-spacing: 0.04em; line-height: 1; margin: 0 0 6px; }
  .when { font-family: "Anton", Impact, sans-serif; color: var(--red); font-size: clamp(48px, 12vw, 104px); line-height: 1; margin: 0; }
  .whenk { color: var(--muted); font-weight: 800; font-size: 13px; letter-spacing: 0.1em; margin: 8px 0 22px; }
  .cta { display: inline-block; background: var(--tag); color: var(--ink); text-decoration: none; border: 0; cursor: pointer; font-family: "Anton", Impact, sans-serif; font-size: clamp(28px, 6vw, 44px); line-height: 1.2; padding: 12px 28px; border-radius: 6px; }
  .cta small { display: block; font-family: "Inter", sans-serif; font-weight: 800; font-size: 14px; letter-spacing: 0.08em; }
  .links { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 20px; }
  .links a { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; color: var(--text); text-decoration: none; font-weight: 800; font-size: 15px; }
  .links a:hover, .links a:focus-visible { border-color: var(--tag); }
  .help { color: var(--muted); font-size: 15px; margin: 16px 0 0; }
  .tel { color: var(--text); font-weight: 900; white-space: nowrap; }
  .nk { border: 4px solid var(--red); padding: 14px 18px; margin: 28px auto 0; max-width: 680px; background: var(--panel); }
  .nk b { font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: 26px; letter-spacing: 0.02em; }
  .nk p { margin: 6px 0 0; color: var(--muted); font-size: 15px; }
  nav { position: sticky; top: 0; z-index: 2; background: rgba(11,11,12,0.95); border-bottom: 1px solid var(--line); padding: 10px 0; }
  nav .wrap { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
  .navlinks { display: flex; gap: 16px; overflow-x: auto; white-space: nowrap; scrollbar-width: none; max-width: 100%; }
  .navlinks a { color: var(--text); text-decoration: none; font-weight: 800; font-size: 14px; letter-spacing: 0.04em; }
  #q { flex: 1 1 220px; min-width: 0; background: var(--panel); color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; font: inherit; }
  h2 { font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: clamp(34px, 7vw, 54px); margin: 48px 0 6px; line-height: 1; scroll-margin-top: 120px; }
  h2 + p { color: var(--muted); margin: 0 0 18px; }
  .lede { color: var(--text); font-size: 20px; font-weight: 800; }
  h3 { font-size: 17px; letter-spacing: 0.06em; font-weight: 900; margin: 30px 0 10px; color: var(--muted); }
  h3 b { color: var(--red); font-family: "Anton", Impact, sans-serif; font-weight: 400; font-size: 26px; letter-spacing: 0.02em; }
  ul { list-style: none; margin: 0; padding: 0; }
  section[id], .rc { scroll-margin-top: 120px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 8px; }
  .chips a { border: 1px solid var(--line); border-radius: 999px; padding: 4px 11px; color: var(--text); text-decoration: none; font-weight: 800; font-size: 13px; letter-spacing: 0.03em; }
  .chips a span { color: var(--muted); margin-left: 6px; }
  summary { cursor: pointer; font-weight: 900; letter-spacing: 0.06em; color: var(--muted); padding: 6px 0; }
  .legend ul { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px; margin: 8px 0 4px; }
  .legend li { color: var(--muted); font-size: 14px; }
  .rc { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; margin: 0 0 10px; }
  .rc:target { outline: 3px solid var(--tag); }
  .exn { display: inline-block; background: var(--tag); color: var(--ink); font-weight: 900; font-size: 12px; letter-spacing: 0.06em; padding: 2px 8px; margin-right: 8px; }
  .st { display: inline-block; font-weight: 900; font-size: 11px; letter-spacing: 0.1em; padding: 1px 7px; border: 2px solid currentColor; border-radius: 3px; }
  .st-QUOTE { color: #f59e0b; } .st-COURT { color: #60a5fa; } .st-REPORTED { color: #d6d3d1; } .st-DATA { color: #2dd4bf; }
  .st-ESTIMATE { color: #c084fc; } .st-OFFICIAL { color: #4ade80; } .st-PROPOSED { color: #fb923c; } .st-LAW { color: #93c5fd; } .st-WIN { color: var(--win); }
  .cap { font-weight: 800; font-size: 19px; line-height: 1.3; margin: 8px 0 6px; }
  .src { margin: 0; font-size: 14px; color: var(--muted); overflow-wrap: anywhere; }
  .note { margin: 8px 0 0; font-size: 14px; color: var(--muted); border-left: 3px solid var(--line); padding-left: 10px; }
  .rid { margin: 8px 0 0; font-size: 12px; color: var(--muted); }
  .rid a { color: var(--muted); }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
  .pair > div { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }
  .lbl { display: inline-block; background: var(--text); color: var(--ink); font-weight: 900; font-size: 12px; letter-spacing: 0.12em; padding: 2px 8px; margin-bottom: 8px; }
  .lbl.red { background: var(--red); color: #fff; }
  .trick { margin-bottom: 18px; }
  .tn { font-weight: 900; margin: 0; color: var(--muted); letter-spacing: 0.04em; }
  .counter { font-family: "Anton", Impact, sans-serif; font-size: 28px; color: var(--red); margin: 2px 0 10px; line-height: 1.1; white-space: pre-line; }
  .sb li { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding: 10px 0; font-weight: 800; }
  .sb a { color: var(--win); text-decoration: none; white-space: nowrap; }
  .rights li { background: var(--panel); border-left: 4px solid var(--tag); padding: 10px 14px; margin-bottom: 8px; }
  .box { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 4px 20px 20px; margin-top: 48px; }
  .box h2 { margin-top: 16px; }
  .ways li { margin: 0 0 10px; }
  #exhibits ul { margin-top: 12px; }
  footer.wrap { color: var(--muted); font-size: 14px; border-top: 1px solid var(--line); margin-top: 60px; padding-top: 24px; padding-bottom: 60px; }
  .by a { display: inline-flex; align-items: center; gap: 10px; color: var(--text); font-weight: 900; letter-spacing: 0.06em; text-decoration: none; }
  .hide { display: none !important; }
  @media (max-width: 640px) {
    body { font-size: 16px; } .cap { font-size: 17px; }
    .pair, .legend ul { grid-template-columns: 1fr; }
    .links { grid-template-columns: 1fr 1fr; }
    .sb li { flex-direction: column; gap: 2px; }
    .sb a { white-space: normal; }
  }
</style>
</head>
<body>
<header class="wrap">
  <h1>VOTE. THEM. <span>OUT.</span></h1>
  <section class="vote" id="vote" aria-label="How to vote">
    <p class="whenl">ELECTION DAY</p>
    <p class="when">TUESDAY, NOV 3</p>
    <p class="whenk">2026 MIDTERMS · EVERY HOUSE SEAT · ABOUT A THIRD OF THE SENATE</p>
    <a class="cta" href="${VOTE.check}" rel="noopener">VOTE.ORG<small>CHECK YOUR REGISTRATION TODAY</small></a>
    <div class="links">${quick}</div>
    <p class="help">Deadlines and rules differ by state, so check yours today. Missed a deadline? Some states let you register at the polls.</p>
  </section>${noKings}
</header>
<nav><div class="wrap">
  <div class="navlinks"><a href="#rights">YOUR RIGHTS</a><a href="#case">THE CASE</a><a href="#playbook">PLAYBOOK</a><a href="#add">ADD A RECEIPT</a><a href="#video">VIDEO EXHIBITS</a></div>
  <input id="q" type="search" placeholder="Search the receipts (Medicaid, Epstein, tariffs…)" aria-label="Search the receipts">
</div></nav>
<main class="wrap">
  <h2 id="rights">YOUR RIGHTS AT THE POLLS</h2>
  <p>Problems voting? Election Protection: ${tel(h.en)} · en español ${tel(h.es)} · Asian languages ${tel(h.asian)} · Arabic ${tel(h.arabic)} (<a href="${esc(h.source)}" rel="noopener">866ourvote.org</a>)</p>
  <ul class="rights">
    <li>${esc(f.in_line.text)} (<a href="${esc(f.in_line.source)}" rel="noopener">source</a>)</li>
    <li>${esc(f.provisional.text)} (<a href="${esc(f.provisional.source)}" rel="noopener">source</a>)</li>
    <li>${esc(f.intimidation.text)} (<a href="${esc(f.intimidation.source)}" rel="noopener">source</a>)</li>
    <li>Registration deadlines and voting rules differ by state. Check yours at <a href="https://www.vote.org" rel="noopener">vote.org</a> or <a href="https://www.canivote.org" rel="noopener">canivote.org</a>.</li>
  </ul>

  <h2 id="case">THE CASE AGAINST THEM</h2>
  <p class="lede">Not opinions. ${total} receipts, each linked to its source and labeled with what kind of evidence it is.</p>
  <details class="legend"><summary>WHAT THE LABELS MEAN</summary><ul>${legend}</ul></details>
  <div class="chips">${chips}</div>
  ${byTopic}

  <h2 id="confessions">EVERY ACCUSATION IS A CONFESSION</h2>
  <p>What they said, then what they did.</p>
  ${confessions}

  <h2 id="playbook">THEIR PLAYBOOK</h2>
  <p>How they'll try to keep you home, and what beats it.</p>
  ${playbook}

  <h2 id="scoreboard">THE SCOREBOARD</h2>
  <p>When we show up, we win.</p>
  <ul class="sb">${scoreboard}</ul>

  <section class="box" id="bring">
    <h2>BRING THREE PEOPLE</h2>
    <p>They're betting you stay home, and your friends too. Text three people today and make a plan together: when you're voting, where, and how you're getting there.</p>
    <button class="cta" id="share" type="button">SEND THIS PAGE</button>
  </section>

  <section class="box" id="add">
    <h2>ADD A RECEIPT</h2>
    <p>This list is public and correctable. Found one we're missing, or one we got wrong?</p>
    <ul class="ways">
      <li><b>No code:</b> fill in <a href="${FORM.receipt}" rel="noopener">the receipt form</a>. You need a free GitHub account.</li>
      <li><b>Several at once, or your AI agent's work:</b> use <a href="${GUIDE}#the-format" rel="noopener">the receipt format</a> and <a href="${GUIDE}#using-an-ai-agent" rel="noopener">the prompt for agents</a>, then paste the JSON into <a href="${FORM.json}" rel="noopener">the JSON form</a> or open a pull request.</li>
      <li><b>Something wrong?</b> Every receipt has a "correct this" link.</li>
    </ul>
    <p>The bar is the source, not the outrage: original outlets and records, honest labels, and captions that say no more than the source does.</p>
  </section>

  <h2 id="video">THE VIDEO</h2>
  <p>VOTE. THEM. OUT. is also a video${VIDEO ? `: <a href="${VIDEO}" rel="noopener">watch it</a>` : ""}. Paused on an EXHIBIT number? They're all here, in the order they appear.</p>
  <details id="exhibits"><summary>ALL ${exhibits.length} EXHIBITS</summary><ul>${exhibitList}
  </ul></details>
</main>
<footer class="wrap">
  <p class="by"><a href="${CHANNEL}" rel="noopener">${MARK}OPPOSABLE MEANING</a></p>
  <p><b>Found an error or a better source?</b> Every receipt has a "correct this" link, or open an issue at <a href="${REPO}" rel="noopener">${REPO.replace("https://", "")}</a>.</p>
  <p>Take it with you: <a href="/vote/receipts.json">every receipt as JSON</a> (CC BY 4.0) · <a href="/vote/receipt.schema.json">the receipt format</a> · <a href="${REPO}" rel="noopener">the code</a> (MIT). Protest counts: Crowd Counting Consortium (Harvard Ash Center / UConn), CC0.</p>
</footer>
<script>
  // No Kings: the Oct 17 note until that day is over everywhere, then the standing one
  const after = new Date() >= new Date("2026-10-18T12:00:00Z");
  document.getElementById("nk-before")?.classList.toggle("hide", after);
  document.getElementById("nk-after")?.classList.toggle("hide", !after);
  // live filter
  const q = document.getElementById("q");
  const items = [...document.querySelectorAll(".rc, .pair, .trick")];
  q.addEventListener("input", () => {
    const t = q.value.trim().toLowerCase();
    items.forEach((el) => el.classList.toggle("hide", !!t && !el.textContent.toLowerCase().includes(t)));
    document.querySelectorAll(".beat").forEach((s) => s.classList.toggle("hide", !!t && !s.querySelector(".rc:not(.hide)")));
  });
  // a link to an exhibit opens the list it's in
  const reveal = () => {
    const el = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    const d = el && el.closest("details");
    if (d && !d.open) { d.open = true; el.scrollIntoView(); }
  };
  addEventListener("hashchange", reveal);
  reveal();
  // send this page: the share sheet where there is one, otherwise copy the link
  const share = document.getElementById("share");
  share.addEventListener("click", async () => {
    const msg = { title: document.title, text: "Election Day is Tuesday, Nov 3. Check your registration at vote.org. The receipts:", url: "${SITE}" };
    try {
      if (navigator.share) await navigator.share(msg);
      else { await navigator.clipboard.writeText(msg.url); share.textContent = "LINK COPIED"; }
    } catch {}
  });
</script>
</body>
</html>
`;

mkdirSync(join(OUT, "fonts"), { recursive: true });
for (const font of ["Anton-Regular.ttf", "Anton-OFL.txt", "Inter.ttf", "Inter-OFL.txt"]) cpSync(join(ROOT, "assets/fonts", font), join(OUT, "fonts", font));
writeFileSync(join(OUT, "index.html"), html);
writeFileSync(join(OUT, "receipts.json"), JSON.stringify(data, null, 1));
writeFileSync(join(OUT, "receipt.schema.json"), JSON.stringify(schema(data), null, 1) + "\n");

// Cloudflare Pages: the root goes to the page (302: the root may get its own page later). No
// /vote -> /vote/ rule: if Pages matched it against /vote/ too, it would loop; asset paths are absolute.
writeFileSync(join(DOCS, "_redirects"), "/ /vote/ 302\n");
writeFileSync(join(DOCS, "_headers"), [
  "/vote/fonts/*",
  "  Cache-Control: public, max-age=31536000, immutable",
  "/vote/receipts.json",
  "  Access-Control-Allow-Origin: *",
  "/vote/receipt.schema.json",
  "  Access-Control-Allow-Origin: *",
  "/*",
  "  X-Content-Type-Options: nosniff",
  "  Referrer-Policy: strict-origin-when-cross-origin",
  "",
].join("\n"));
// fallback for hosts that ignore _redirects
writeFileSync(join(DOCS, "index.html"), `<!doctype html><meta charset="utf-8"><title>VOTE. THEM. OUT.</title><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url=vote/"><link rel="canonical" href="${SITE}"><a href="vote/">The receipts</a>\n`);
writeFileSync(join(DOCS, ".nojekyll"), "");
for (const icon of ["favicon.svg", "favicon.ico", "apple-touch-icon.png"]) cpSync(join(ROOT, "brand", icon), join(DOCS, icon));

// the contributor docs list today's labels and topics
const fill = (text, name, body) => {
  const re = new RegExp(`(<!-- ${name}: [^>]*-->\\n)[\\s\\S]*?(\\n<!-- /${name} -->)`);
  if (!re.test(text)) console.warn(`CONTRIBUTING.md has no ${name} markers; skipped`);
  return text.replace(re, (_, open, close) => open + body + close);
};
const guide = join(ROOT, "CONTRIBUTING.md");
writeFileSync(guide, fill(fill(readFileSync(guide, "utf8"), "labels", labelTable()), "topics", topicTable(data)));
mkdirSync(join(ROOT, ".github/ISSUE_TEMPLATE"), { recursive: true });
writeFileSync(join(ROOT, ".github/ISSUE_TEMPLATE/new-receipt.yml"), receiptForm(data));
console.log(`site: docs/vote/index.html (${total} receipts, ${exhibits.length} exhibits) + receipt.schema.json, CONTRIBUTING.md tables, receipt form`);
