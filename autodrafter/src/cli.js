#!/usr/bin/env node
// eBay auto-drafter CLI.
//
// Usage:
//   node src/cli.js <photos-dir> [--out <dir>] [--max-photos <n>] [--mock]
//
// <photos-dir> layout: one subfolder per item, each containing that item's
// photos. Name the folder whatever you'd call the item ("nike hoodie XL") —
// the name is passed to the model as a hint. Loose images directly in
// <photos-dir> are treated as a single item.

import fs from "fs";
import path from "path";
import { draftListing, isImage } from "./analyze.js";
import { draftsToCsv } from "./csv.js";

function parseArgs(argv) {
  const opts = { out: "drafts", maxPhotos: 8, mock: false, input: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--out") opts.out = argv[++i];
    else if (a === "--max-photos") opts.maxPhotos = Number(argv[++i]);
    else if (a === "--mock") opts.mock = true;
    else if (a === "--help" || a === "-h") return null;
    else if (!opts.input) opts.input = a;
    else {
      console.error(`Unknown argument: ${a}`);
      return null;
    }
  }
  return opts.input ? opts : null;
}

function findItems(inputDir) {
  const entries = fs.readdirSync(inputDir, { withFileTypes: true });
  const items = [];

  for (const e of entries.filter((e) => e.isDirectory())) {
    const dir = path.join(inputDir, e.name);
    const photos = fs
      .readdirSync(dir)
      .filter(isImage)
      .sort()
      .map((f) => path.join(dir, f));
    if (photos.length) items.push({ name: e.name, photos });
  }

  const loose = entries
    .filter((e) => e.isFile() && isImage(e.name))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((e) => path.join(inputDir, e.name));
  if (loose.length) items.push({ name: path.basename(path.resolve(inputDir)), photos: loose });

  return items;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (!opts) {
    console.log("Usage: autodraft <photos-dir> [--out <dir>] [--max-photos <n>] [--mock]");
    process.exit(1);
  }
  if (!opts.mock && !process.env.ANTHROPIC_API_KEY) {
    console.error(
      "ANTHROPIC_API_KEY is not set. Get a key at https://platform.claude.com and run:\n" +
        "  export ANTHROPIC_API_KEY=sk-ant-...\n" +
        "or use --mock to test the pipeline without API calls.",
    );
    process.exit(1);
  }

  const items = findItems(opts.input);
  if (!items.length) {
    console.error(`No photos found in ${opts.input}. Expected item subfolders with .jpg/.png/.webp files.`);
    process.exit(1);
  }

  fs.mkdirSync(opts.out, { recursive: true });
  console.log(`Found ${items.length} item(s). Drafting${opts.mock ? " (mock mode)" : ""}...\n`);

  const results = [];
  const failures = [];
  for (const item of items) {
    const photos = item.photos.slice(0, opts.maxPhotos);
    process.stdout.write(`- ${item.name} (${photos.length} photo(s))... `);
    try {
      const draft = await draftListing(photos, { hint: item.name, mock: opts.mock });
      const jsonPath = path.join(opts.out, `${item.name.replace(/[^\w\- ]+/g, "_")}.json`);
      fs.writeFileSync(jsonPath, JSON.stringify(draft, null, 2));
      results.push({ item: item.name, draft });
      console.log(`ok → "${draft.title}" ($${draft.price.suggested})`);
    } catch (err) {
      failures.push({ item: item.name, error: err.message });
      console.log(`FAILED: ${err.message}`);
    }
  }

  if (results.length) {
    const csvPath = path.join(opts.out, "drafts.csv");
    fs.writeFileSync(csvPath, draftsToCsv(results));
    console.log(`\n${results.length} draft(s) written to ${opts.out}/ (per-item JSON + drafts.csv)`);
    console.log("Review each draft, then create the listings in eBay (and crosslist via Flyp).");
  }
  if (failures.length) {
    console.log(`\n${failures.length} item(s) failed — rerun after fixing:`);
    for (const f of failures) console.log(`  - ${f.item}: ${f.error}`);
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
