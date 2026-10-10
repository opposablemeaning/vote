# Contributing receipts

This list is public so it can be checked and corrected. A wrong receipt hurts the whole thing, so the bar is the source, not the outrage.

## Rules

1. **Every receipt needs a source URL.** Use the original outlet or the primary record (court opinion, roll call, agency release, transcript), not a repost, aggregator, or social screenshot. If the original is paywalled, link it anyway and add a second, open source in `also`.
2. **Every receipt needs an honest status label:** `QUOTE`, `COURT RULING`, `OFFICIAL`, `REPORTED`, `DATA`, `ESTIMATE`, `PROPOSED`, or `LAW` (see the README). Projections are `ESTIMATE`. Allegations are `REPORTED`, and the caption says "alleged" where it matters.
3. **The caption must say what the source says,** no more. Put exact quotes in quotation marks. Put caveats in `note`.
4. **They're receipts, not verdicts.** Don't call anything a crime unless a court has. Don't name or imply wrongdoing by private individuals.
5. **No content that targets people for who they are.** Receipts are about officials, governments, votes, money, and policy.
6. **Corrections are as welcome as additions.** If a receipt is wrong, outdated, or overstated, open an issue or PR that fixes or removes it.

## Format

Add an object to `receipts` in `data/receipts.json`:

```json
{
  "id": "hc11",
  "beat": "healthcare",
  "status": "DATA",
  "caption": "What the source shows, in plain words",
  "outlet": "KFF",
  "date": "2026-10-01",
  "url": "https://...",
  "also": "https://... (optional second source)",
  "note": "optional: exact quote, caveats, context"
}
```

- `beat` is one of the `beats` ids in the same file.
- `id` is unique and stable. Don't renumber existing receipts; the video and the site link to them.
- Then run `node scripts/build-site.mjs` to regenerate the site, and include the `docs/` changes in your PR.
