// JSON schema for a listing draft, used with output_config.format so the
// model's response is guaranteed to parse. Structured outputs require
// additionalProperties: false and every key listed in `required`.

export const LISTING_SCHEMA = {
  type: "object",
  properties: {
    title: {
      type: "string",
      description:
        "eBay listing title, max 80 characters. Front-load brand, model, size, and key search terms. No promotional filler like 'L@@K' or 'WOW'.",
    },
    condition: {
      type: "string",
      enum: [
        "New with tags",
        "New without tags",
        "New other",
        "Used - Excellent",
        "Used - Good",
        "Used - Fair",
        "For parts or not working",
      ],
      description: "Condition as visible in the photos. When unsure between two grades, pick the lower one.",
    },
    category: {
      type: "string",
      description:
        "Suggested eBay category path, e.g. 'Clothing, Shoes & Accessories > Men > Men's Clothing > Shirts > Casual Button-Down Shirts'.",
    },
    brand: { type: "string", description: "Brand name, or 'Unbranded' if none is visible." },
    item_specifics: {
      type: "array",
      description:
        "eBay item specifics visible or inferable from the photos: Size, Color, Material, Style, Model, Type, etc.",
      items: {
        type: "object",
        properties: {
          name: { type: "string" },
          value: { type: "string" },
        },
        required: ["name", "value"],
        additionalProperties: false,
      },
    },
    description: {
      type: "string",
      description:
        "Buyer-facing description in plain text: what the item is, measurements/size if visible, condition details, and any flaws. Honest and specific; no invented details.",
    },
    flaws: {
      type: "array",
      items: { type: "string" },
      description: "Each visible flaw or sign of wear (stains, pilling, scratches, missing parts). Empty if none visible.",
    },
    price: {
      type: "object",
      description: "Estimated resale price range in USD based on the item type, brand, and condition.",
      properties: {
        suggested: { type: "number" },
        low: { type: "number" },
        high: { type: "number" },
      },
      required: ["suggested", "low", "high"],
      additionalProperties: false,
    },
    keywords: {
      type: "array",
      items: { type: "string" },
      description: "Extra search keywords not already in the title.",
    },
    confidence_notes: {
      type: "string",
      description:
        "Anything the seller should verify before publishing (e.g. 'could not read the size tag', 'authenticate before listing').",
    },
  },
  required: [
    "title",
    "condition",
    "category",
    "brand",
    "item_specifics",
    "description",
    "flaws",
    "price",
    "keywords",
    "confidence_notes",
  ],
  additionalProperties: false,
};
