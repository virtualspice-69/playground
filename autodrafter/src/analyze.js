import fs from "fs";
import path from "path";
import Anthropic from "@anthropic-ai/sdk";
import { LISTING_SCHEMA } from "./schema.js";

const MODEL = process.env.AUTODRAFT_MODEL || "claude-opus-4-8";
const MEDIA_TYPES = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".gif": "image/gif",
};

export function isImage(file) {
  return Object.hasOwn(MEDIA_TYPES, path.extname(file).toLowerCase());
}

function imageBlock(filePath) {
  return {
    type: "image",
    source: {
      type: "base64",
      media_type: MEDIA_TYPES[path.extname(filePath).toLowerCase()],
      data: fs.readFileSync(filePath).toString("base64"),
    },
  };
}

const SYSTEM_PROMPT = `You are an expert eBay reseller's listing assistant. You look at photos of an item and produce a ready-to-review draft listing.

Rules:
- Only describe what you can actually see or read in the photos. Never invent sizes, model numbers, or materials.
- Titles are max 80 characters and front-load the terms buyers search for: brand, item type, size, color, model.
- Grade condition honestly and call out every visible flaw — accurate flaw disclosure prevents returns.
- Price estimates should reflect typical sold prices for comparable used items on eBay, not retail price.
- Put anything you are unsure about in confidence_notes so the seller can verify it before publishing.`;

/**
 * Analyze one item's photos and return a listing draft object.
 * @param {string[]} photoPaths absolute paths to the item's photos
 * @param {object} opts { hint?: string, mock?: boolean }
 */
export async function draftListing(photoPaths, opts = {}) {
  if (opts.mock) return mockDraft(photoPaths, opts.hint);

  const client = new Anthropic();
  const content = photoPaths.map(imageBlock);
  content.push({
    type: "text",
    text:
      `Create an eBay draft listing from these ${photoPaths.length} photos of one item.` +
      (opts.hint ? ` Seller's note about this item: ${opts.hint}` : ""),
  });

  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 8000,
    thinking: { type: "adaptive" },
    system: SYSTEM_PROMPT,
    output_config: { format: { type: "json_schema", schema: LISTING_SCHEMA } },
    messages: [{ role: "user", content }],
  });

  if (response.stop_reason === "refusal") {
    throw new Error("The model declined to analyze these photos.");
  }
  if (response.stop_reason === "max_tokens") {
    throw new Error("Response was truncated (max_tokens). Try fewer photos for this item.");
  }

  const text = response.content.find((b) => b.type === "text")?.text;
  if (!text) throw new Error("No text block in model response.");
  const draft = JSON.parse(text);

  // eBay hard limit — enforce even though the prompt asks for it.
  if (draft.title.length > 80) draft.title = draft.title.slice(0, 80).trim();

  draft._meta = {
    model: response.model,
    photos: photoPaths.map((p) => path.basename(p)),
    usage: {
      input_tokens: response.usage.input_tokens,
      output_tokens: response.usage.output_tokens,
    },
    generated_at: new Date().toISOString(),
  };
  return draft;
}

/** Offline stand-in so the pipeline can be tested without an API key. */
function mockDraft(photoPaths, hint) {
  const name = hint || path.basename(path.dirname(photoPaths[0]));
  return {
    title: `${name} (mock draft)`.slice(0, 80),
    condition: "Used - Good",
    category: "Everything Else > Test Listings",
    brand: "Unbranded",
    item_specifics: [{ name: "Type", value: name }],
    description: `Mock draft for "${name}" generated without calling the API. Run without --mock to get a real draft.`,
    flaws: [],
    price: { suggested: 19.99, low: 14.99, high: 24.99 },
    keywords: [name.toLowerCase()],
    confidence_notes: "Mock mode — no photos were analyzed.",
    _meta: {
      model: "mock",
      photos: photoPaths.map((p) => path.basename(p)),
      usage: { input_tokens: 0, output_tokens: 0 },
      generated_at: new Date().toISOString(),
    },
  };
}
