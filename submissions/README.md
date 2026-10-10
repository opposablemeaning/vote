# Submissions

Pull requests add new receipts here: one JSON file holding an array of receipts in [the receipt format](../CONTRIBUTING.md#the-format), named for what it covers (like `medicaid-cuts.json`). Check it first with `node scripts/receipts.mjs check submissions/<file>.json`.

Maintainers merge a file with `node scripts/receipts.mjs add submissions/<file>.json`, which assigns ids, adds the receipts to `data/receipts.json` and deletes the file.
