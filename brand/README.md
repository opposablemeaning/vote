# Opposable Meaning brand

The mark is an O split in two, its halves pushed out of line, holding the point. Opposition holding meaning.

Every file here comes from `scripts/build-brand.mjs`. Change the geometry or colors there and run `node scripts/build-brand.mjs`, then `node scripts/build-site.mjs` to update the site's icons.

| File | Use |
|---|---|
| `avatar-800.png` | Profile picture for YouTube, GitHub and Google (all three crop it to a circle) |
| `avatar-light-800.png` | The same on white, if a light picture is ever needed |
| `banner-2560x1440.png` | YouTube banner. Everything sits inside the 1546 x 423 center that every device shows |
| `watermark-150.png` | YouTube video watermark (Studio: Customization, Branding) |
| `mark-on-dark.svg` | The mark alone, for dark backgrounds: off-white halves, red point |
| `mark-on-light.svg` | The mark alone, for light backgrounds: ink halves, red point |
| `avatar.svg`, `avatar-light.svg` | Sources for the two profile pictures |
| `favicon.svg`, `favicon.ico`, `apple-touch-icon.png` | Site icons; `build-site.mjs` copies them into `docs/` |

**Colors:** ink `#0b0b0c`, off-white `#f5f5f4`, red `#e3122b`. The type next to the mark is Anton.

**Rules:**
- Keep the point red, and keep the halves one color: off-white on dark, ink on light.
- Don't rotate, stretch or outline the mark, and don't line the halves back up. The offset is the idea.

The Opposable Meaning name and logo are not covered by this repository's MIT or CC BY licenses.
