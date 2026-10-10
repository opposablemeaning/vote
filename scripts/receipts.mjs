// The receipt format: what a valid receipt is, in one place. build-site.mjs publishes it as JSON
// Schema (docs/vote/receipt.schema.json), as the tables in CONTRIBUTING.md and as the topic list in
// the receipt form. Run this file to check receipts or to merge a submission.
//
//   node scripts/receipts.mjs check [file.json ...]   check data/receipts.json and submissions
//                                                     (every submissions/*.json unless files are named)
//   node scripts/receipts.mjs add submissions/x.json  give each receipt an id, add it to
//                                                     data/receipts.json, delete the file

import { readFileSync, writeFileSync, readdirSync, existsSync, rmSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DATA = join(ROOT, "data/receipts.json");
const SUBMISSIONS = join(ROOT, "submissions");

export const SITE = "https://opposablemeaning.com/vote/";
export const REPO = "https://github.com/opposablemeaning/vote";

// status labels, in the order the docs list them
export const LABELS = [
  ["QUOTE", "Their own words, from a recording, transcript or post"],
  ["COURT RULING", "A decision by a judge, jury or court"],
  ["COURT ORDER", "An interim court order (like the ICJ's provisional measures), not a final ruling"],
  ["COURT FILING", "An allegation in a court filing, such as an indictment"],
  ["OFFICIAL", "A government record: a vote tally, an order, an agency release"],
  ["REPORTED", "Reporting by a news outlet"],
  ["DATA", "Published statistics"],
  ["ESTIMATE", "A projection or model (CBO, KFF, researchers), labeled as one"],
  ["PROPOSED", "Proposed, not done"],
  ["LAW", "Enacted law"],
];
const STATUSES = LABELS.map(([s]) => s);
const FIELDS = ["id", "beat", "status", "caption", "outlet", "date", "url", "also", "note", "win", "short"];
const REQUIRED = ["beat", "status", "caption", "outlet", "date", "url"];
const LIMITS = { caption: 160, outlet: 80, note: 600, short: 100 };
// pattern strings, so the schema gets them unescaped
const ID = "^[a-z]+\\d+$";
const DATE = "^\\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\\d|3[01]))?)?$";
const LINK = "^https?://\\S+$";
const matches = (pattern, s) => new RegExp(pattern).test(s);

// what's wrong with one receipt, in words a contributor can act on
export function problems(r, topics) {
  if (!r || typeof r !== "object" || Array.isArray(r)) return ["isn't a JSON object"];
  const out = [];
  for (const k of Object.keys(r)) if (!FIELDS.includes(k)) out.push(`unknown field "${k}"`);
  for (const k of REQUIRED) if (typeof r[k] !== "string" || !r[k].trim()) out.push(`"${k}" is missing`);
  for (const [k, max] of Object.entries(LIMITS)) {
    if (r[k] === undefined) continue;
    if (typeof r[k] !== "string") out.push(`"${k}" must be text`);
    else if (r[k].length > max) out.push(`"${k}" is ${r[k].length} characters (at most ${max})`);
  }
  if (r.id !== undefined && !(typeof r.id === "string" && matches(ID, r.id))) out.push(`"id" must be letters then digits, like "c12"`);
  if (typeof r.beat === "string" && r.beat && !topics.includes(r.beat)) out.push(`"beat": "${r.beat}" isn't a topic id`);
  if (typeof r.status === "string" && r.status && !STATUSES.includes(r.status)) out.push(`"status": "${r.status}" isn't one of ${STATUSES.join(", ")}`);
  if (typeof r.date === "string" && r.date && !matches(DATE, r.date)) out.push(`"date" must be YYYY-MM-DD`);
  const links = [["url", r.url], ...[].concat(r.also ?? []).map((u) => ["also", u])];
  for (const [k, u] of links) {
    if (k === "url" && (typeof u !== "string" || !u.trim())) continue; // reported as missing above
    if (typeof u !== "string" || !matches(LINK, u)) out.push(`"${k}" must be a full link starting with https://`);
    else if (/\.\.\.|…|example\.(com|org)/.test(u)) out.push(`"${k}" looks like a placeholder: ${u}`);
  }
  if (Array.isArray(r.also) && !r.also.length) out.push(`"also" is an empty list`);
  if (r.win !== undefined && typeof r.win !== "boolean") out.push(`"win" must be true or false`);
  return out;
}

// the stored list: every receipt valid, with a unique id
function checkData(data) {
  const topics = data.beats.map((b) => b.id);
  const errors = [];
  if (new Set(topics).size !== topics.length) errors.push("two topics share an id");
  const seen = new Set();
  data.receipts.forEach((r, i) => {
    const where = r?.id || `receipt #${i + 1}`;
    if (!r?.id) errors.push(`${where}: "id" is missing`);
    else if (seen.has(r.id)) errors.push(`${where}: id used twice`);
    seen.add(r?.id);
    for (const p of problems(r, topics)) errors.push(`${where}: ${p}`);
  });
  return errors;
}

// a submission: an array of new receipts, checked against what's already on the list
const sameSource = (u) => u.trim().toLowerCase().replace(/^https?:\/\/(www\.)?/, "").replace(/#.*$/, "").replace(/\/$/, "");
export function checkSubmission(list, data) {
  const errors = [];
  const warnings = [];
  if (!Array.isArray(list)) return { errors: ["must be a JSON array of receipts: [ { ... }, { ... } ]"], warnings };
  if (!list.length) errors.push("the array is empty");
  const topics = data.beats.map((b) => b.id);
  const ids = new Set(data.receipts.map((r) => r.id));
  const listed = new Map(data.receipts.map((r) => [sameSource(r.url), r]));
  const here = new Map();
  list.forEach((r, i) => {
    const where = `#${i + 1}${typeof r?.caption === "string" ? ` "${r.caption.slice(0, 50)}"` : ""}`;
    for (const p of problems(r, topics)) errors.push(`${where}: ${p}`);
    if (r?.id && ids.has(r.id)) errors.push(`${where}: id "${r.id}" is taken (leave ids out of new receipts)`);
    if (typeof r?.url !== "string" || !r.url.trim()) return;
    const u = sameSource(r.url);
    if (listed.has(u)) warnings.push(`${where}: same source as ${listed.get(u).id} ("${listed.get(u).caption.slice(0, 60)}"). Fine if it's a different claim.`);
    if (here.has(u)) warnings.push(`${where}: same source as #${here.get(u)} in this file`);
    here.set(u, i + 1);
  });
  return { errors, warnings };
}

function readJson(file) {
  try {
    return { value: JSON.parse(readFileSync(file, "utf8")) };
  } catch (e) {
    return { error: e.code === "ENOENT" ? "file not found" : `not valid JSON (${e.message})` };
  }
}

function report(name, what, errors, warnings) {
  console.log(`${errors.length ? "✗" : "✓"} ${name}${what ? `: ${what}` : ""}${errors.length ? `, ${errors.length} to fix` : ""}`);
  for (const e of errors) console.log(`    ${e}`);
  for (const w of warnings) console.log(`    note: ${w}`);
}

function check(files, data) {
  const dataErrors = checkData(data);
  report("data/receipts.json", `${data.receipts.length} receipts`, dataErrors, []);
  let failed = dataErrors.length > 0;
  const subs = files.length ? files : existsSync(SUBMISSIONS) ? readdirSync(SUBMISSIONS).filter((f) => f.endsWith(".json")).map((f) => join(SUBMISSIONS, f)) : [];
  for (const file of subs) {
    const { value, error } = readJson(file);
    const { errors, warnings } = error ? { errors: [error], warnings: [] } : checkSubmission(value, data);
    report(relative(process.cwd(), file), Array.isArray(value) ? `${value.length} receipts` : "", errors, warnings);
    failed ||= errors.length > 0;
  }
  return failed;
}

// ids continue the topic's existing prefix (corruption: c1, c2 …); a topic with no receipts yet uses its own id
const prefixOf = (id) => id.replace(/\d+$/, "");
function nextId(beat, receipts) {
  const counts = {};
  for (const r of receipts) if (r.beat === beat) counts[prefixOf(r.id)] = (counts[prefixOf(r.id)] || 0) + 1;
  const prefix = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0] || beat.replace(/[^a-z]/g, "");
  const used = receipts.filter((r) => prefixOf(r.id) === prefix).map((r) => Number(r.id.slice(prefix.length)));
  return `${prefix}${Math.max(0, ...used) + 1}`;
}

function add(file, data) {
  const { value, error } = readJson(file);
  const { errors, warnings } = error ? { errors: [error], warnings: [] } : checkSubmission(value, data);
  report(relative(process.cwd(), file), Array.isArray(value) ? `${value.length} receipts` : "", errors, warnings);
  if (errors.length) return true;
  const added = [];
  for (const r of value) {
    const rec = { id: nextId(r.beat, data.receipts) };
    for (const k of FIELDS.slice(1)) if (r[k] !== undefined) rec[k] = r[k];
    // keep each topic's receipts together, in the order they were submitted
    const last = data.receipts.findLastIndex((x) => x.beat === r.beat);
    data.receipts.splice(last < 0 ? data.receipts.length : last + 1, 0, rec);
    added.push(rec.id);
  }
  writeFileSync(DATA, JSON.stringify(data, null, 1) + "\n");
  rmSync(file);
  console.log(`Added ${added.join(", ")} to data/receipts.json and deleted ${relative(process.cwd(), file)}.\nNext: node scripts/build-site.mjs`);
  return false;
}

// the format as JSON Schema, with today's topic ids
export function schema(data) {
  const link = { type: "string", pattern: LINK };
  return {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    $id: `${SITE}receipt.schema.json`,
    title: "Receipts for opposablemeaning.com/vote",
    description: `A submission: a JSON array of receipts. Rules, topics and a prompt for AI agents: ${REPO}/blob/main/CONTRIBUTING.md`,
    type: "array",
    minItems: 1,
    items: { $ref: "#/$defs/receipt" },
    $defs: {
      receipt: {
        type: "object",
        additionalProperties: false,
        required: REQUIRED,
        properties: {
          beat: { description: "Topic id", enum: data.beats.map((b) => b.id) },
          status: { description: `What kind of evidence it is. ${LABELS.map(([s, m]) => `${s}: ${m}.`).join(" ")}`, enum: STATUSES },
          caption: { type: "string", minLength: 1, maxLength: LIMITS.caption, description: "One claim in plain words, saying only what the source says. Exact quotes go in double quotation marks." },
          outlet: { type: "string", minLength: 1, maxLength: LIMITS.outlet, description: "Who published the source: the outlet or the record, e.g. Reuters, Supreme Court opinion, House roll call 123" },
          date: { type: "string", pattern: DATE, description: "When the source was published: YYYY-MM-DD (YYYY-MM or YYYY only when the source gives no day)" },
          url: { ...link, description: "The original source: the outlet or primary record, not a repost, aggregator or screenshot" },
          also: { description: "A second source, or a list of them (use one when url is paywalled)", oneOf: [link, { type: "array", minItems: 1, items: link }] },
          note: { type: "string", maxLength: LIMITS.note, description: "Caveats, context or the exact quote" },
          win: { type: "boolean", description: "true only when the receipt records them being stopped: blocked in court, voted down" },
          id: { type: "string", pattern: ID, description: "Leave it out. Ids are assigned when a submission is merged." },
          short: { type: "string", maxLength: LIMITS.short, description: "A shorter caption for the video. Leave it out." },
        },
      },
    },
  };
}

// the label and topic tables in CONTRIBUTING.md
export const labelTable = () => ["| `status` | What it means |", "|---|---|", ...LABELS.map(([s, m]) => `| \`${s}\` | ${m} |`)].join("\n");
export function topicTable(data) {
  const count = (id) => data.receipts.filter((r) => r.beat === id).length;
  return ["| `beat` | On the page as | Receipts |", "|---|---|---|", ...data.beats.map((b) => `| \`${b.id}\` | ${b.word} | ${count(b.id)} |`)].join("\n");
}

// the no-code issue form; its dropdowns list today's topics and labels
export function receiptForm(data) {
  const q = JSON.stringify; // a JSON string is a valid YAML scalar
  const options = (xs) => xs.map((x) => `        - ${q(x)}`).join("\n");
  const field = (type, id, label, description, extra = "", required = true) => `  - type: ${type}
    id: ${id}
    attributes:
      label: ${q(label)}${description ? `\n      description: ${q(description)}` : ""}${extra}${required ? "\n    validations:\n      required: true" : ""}`;
  return `# Generated by scripts/build-site.mjs from data/receipts.json. Edit it there.
name: New receipt
description: Add one sourced claim to the list. No code needed.
title: "Receipt: "
labels: ["receipt"]
body:
  - type: markdown
    attributes:
      value: ${q(`One claim, one source. The bar is the source, not the outrage: read [the rules](${REPO}/blob/main/CONTRIBUTING.md#the-rules) first.`)}
${field("input", "url", "Source link", "The original outlet or record (court opinion, roll call, agency release, transcript), not a repost, aggregator or screenshot.", `\n      placeholder: "https://"`)}
${field("textarea", "caption", "What does it show?", `One claim in plain words, saying only what the source says (${LIMITS.caption} characters at most). Put exact quotes in quotation marks.`)}
${field("dropdown", "beat", "Topic", "Nothing fits? Pick the last option and say what's missing in the notes.", `\n      options:\n${options([...data.beats.map((b) => `${b.word} (${b.id})`), "Something else"])}`)}
${field("dropdown", "status", "What kind of evidence is it?", "", `\n      options:\n${options(LABELS.map(([s, m]) => `${s}: ${m}`))}`)}
${field("input", "outlet", "Who published it?", "", `\n      placeholder: "Reuters, Supreme Court opinion, House roll call 123"`)}
${field("input", "date", "When was it published?", "", `\n      placeholder: "YYYY-MM-DD"`)}
${field("input", "also", "Second source (optional)", "Especially if the first one is paywalled.", "", false)}
${field("textarea", "note", "Notes (optional)", "Caveats, context or the exact quote.", "", false)}
  - type: checkboxes
    id: checks
    attributes:
      label: Before you send it
      options:
        - label: I opened the source, and it says what my caption says.
          required: true
`;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [cmd, ...files] = process.argv.slice(2);
  const data = JSON.parse(readFileSync(DATA, "utf8"));
  if (cmd === "check") process.exit(check(files, data) ? 1 : 0);
  else if (cmd === "add" && files.length === 1) process.exit(add(files[0], data) ? 1 : 0);
  else {
    console.error("usage: node scripts/receipts.mjs check [file.json ...]\n       node scripts/receipts.mjs add submissions/<file>.json");
    process.exit(2);
  }
}
