// Builds the Opposable Meaning brand files in brand/ from one piece of geometry: an O split in two,
// the halves pushed out of line, holding the point. Needs rsvg-convert and ImageMagick
// (brew install librsvg imagemagick). The banner is rendered by Chrome; set CHROME if it isn't
// in the default macOS location.
//
//   node scripts/build-brand.mjs   ->  brand/mark-on-dark.svg, mark-on-light.svg, avatar*.svg/png,
//                                      favicon.svg, favicon.ico, apple-touch-icon.png,
//                                      watermark-150.png, banner-2560x1440.png

import { writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "brand");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const INK = "#0b0b0c";
const PAPER = "#f5f5f4";
const RED = "#e3122b";
const WHITE = "#ffffff";

// on a 512 grid: two half-rings (outer radius 158, inner 92) sit 9 px either side of center, the
// left one 24 px up and the right one 24 px down, around a dot of radius 44
function mark(halves, dot) {
  const ro = 158, ri = 92, d = 24, g = 9, C = 256;
  const half = (cx, cy, sweep) =>
    `M${cx} ${cy - ro}A${ro} ${ro} 0 0 ${sweep} ${cx} ${cy + ro}L${cx} ${cy + ri}A${ri} ${ri} 0 0 ${1 - sweep} ${cx} ${cy - ri}Z`;
  return `<path d="${half(C - g, C - d, 0)}" fill="${halves}"/><path d="${half(C + g, C + d, 1)}" fill="${halves}"/><circle cx="${C}" cy="${C}" r="44" fill="${dot}"/>`;
}
const svg = (body, viewBox = "0 0 512 512") => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}">${body}</svg>\n`;
// favicons are seen tiny, so the mark fills more of its circle there
const big = (body) => `<g transform="translate(256 256) scale(1.15) translate(-256 -256)">${body}</g>`;

const files = {
  "mark-on-dark.svg": svg(mark(PAPER, RED)),
  "mark-on-light.svg": svg(mark(INK, RED)),
  "avatar.svg": svg(`<rect width="512" height="512" fill="${INK}"/>${mark(PAPER, RED)}`),
  "avatar-light.svg": svg(`<rect width="512" height="512" fill="${WHITE}"/>${mark(INK, RED)}`),
  "favicon.svg": svg(`<circle cx="256" cy="256" r="256" fill="${INK}"/>${big(mark(PAPER, RED))}`),
};
for (const [name, text] of Object.entries(files)) writeFileSync(join(OUT, name), text);

const tmp = mkdtempSync(join(tmpdir(), "brand-"));
const png = (src, out, size) => execFileSync("rsvg-convert", ["-w", String(size), "-h", String(size), "-o", out, join(OUT, src)]);
png("avatar.svg", join(OUT, "avatar-800.png"), 800);
png("avatar-light.svg", join(OUT, "avatar-light-800.png"), 800);
png("avatar.svg", join(OUT, "apple-touch-icon.png"), 180);
png("favicon.svg", join(OUT, "watermark-150.png"), 150);
for (const s of [16, 32, 48]) png("favicon.svg", join(tmp, `f${s}.png`), s);
execFileSync("magick", [16, 32, 48].map((s) => join(tmp, `f${s}.png`)).concat(join(OUT, "favicon.ico")));

// YouTube banner: everything inside the 1546 x 423 area that every device shows
const banner = `<!doctype html><meta charset="utf-8"><style>
  @font-face { font-family: "Anton"; src: url("${pathToFileURL(join(ROOT, "assets/fonts/Anton-Regular.ttf"))}"); }
  html, body { margin: 0; width: 2560px; height: 1440px; background: ${INK}; overflow: hidden; }
  .safe { position: absolute; left: 507px; top: 508px; width: 1546px; height: 423px; display: flex; align-items: center; justify-content: center; gap: 56px; }
  .safe svg { height: 226px; flex: none; }
  .word { font: 400 134px/1 "Anton", sans-serif; color: ${PAPER}; letter-spacing: 0.03em; white-space: nowrap; padding-top: 10px; }
</style><div class="safe">${svg(mark(PAPER, RED), "89 74 334 364")}<div class="word">OPPOSABLE MEANING</div></div>`;
writeFileSync(join(tmp, "banner.html"), banner);
execFileSync(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--user-data-dir=${join(tmp, "profile")}`, "--virtual-time-budget=3000",
  "--window-size=2560,1440", `--screenshot=${join(OUT, "banner-2560x1440.png")}`, pathToFileURL(join(tmp, "banner.html")).href], { stdio: "ignore" });
rmSync(tmp, { recursive: true, force: true });
console.log(`brand: ${Object.keys(files).length} SVGs, avatar-800.png, avatar-light-800.png, apple-touch-icon.png, watermark-150.png, favicon.ico, banner-2560x1440.png`);
