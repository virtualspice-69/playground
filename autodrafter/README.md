# eBay Auto-Drafter

Turn a folder of item photos into ready-to-review eBay draft listings using Claude vision.

You take the photos; this tool writes the title, condition, category, item specifics, description, flaw list, and a suggested price range for every item. You review, publish on eBay, and crosslist with Flyp.

## Setup (one time)

1. Install [Node.js](https://nodejs.org) 18 or newer.
2. In this folder, run:
   ```sh
   npm install
   ```
3. Get a Claude API key at <https://platform.claude.com> and set it:
   ```sh
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

## Daily workflow

1. Make one folder per item and drop that item's photos in it. Name the folder what you'd call the item — the name is given to the AI as a hint:

   ```
   photos/
     nike hoodie XL/
       front.jpg
       back.jpg
       tag.jpg
     levis 501 jeans 34x32/
       front.jpg
       tag.jpg
   ```

2. Run the drafter:

   ```sh
   node src/cli.js photos
   ```

3. Open `drafts/drafts.csv` (Excel/Google Sheets) to review everything at once, or the per-item `.json` files. Each draft includes a **"Verify Before Publishing"** column listing anything the AI wasn't sure about — check those before listing.

4. Create the listings in eBay, then crosslist via Flyp as usual.

## Options

| Flag | Default | What it does |
|---|---|---|
| `--out <dir>` | `drafts` | Where to write the JSON + CSV output |
| `--max-photos <n>` | `8` | Max photos sent to the AI per item (more photos = better drafts but higher cost) |
| `--mock` | off | Test the pipeline without an API key or cost |

Environment variables: `AUTODRAFT_MODEL` overrides the model (default `claude-opus-4-8`).

## What each draft contains

- **Title** — max 80 characters, search-term optimized
- **Condition** — eBay condition grade, judged from the photos (graded conservatively)
- **Category** — suggested eBay category path
- **Item specifics** — brand, size, color, material, etc. as visible in the photos
- **Description** — honest buyer-facing text including all visible flaws
- **Price** — suggested price plus a low/high range
- **Verify Before Publishing** — things the AI couldn't confirm from the photos

The AI is instructed to never invent details it can't see (sizes, model numbers, materials) — anything uncertain lands in the verify column instead.

## Cost

Each item costs roughly 1–3 cents in API usage with 3–8 photos (Claude Opus 4.8 pricing). Drafting 150 listings/week lands around $2–5/week.

## Roadmap

- [ ] Push drafts directly to eBay as draft listings via the eBay Sell API (needs an eBay developer account)
- [ ] Watch folder mode: auto-draft as soon as photos land in the folder
- [ ] Mobile companion (photos on phone → drafts on desktop) — see `../BUSINESS_NOTES.md`
