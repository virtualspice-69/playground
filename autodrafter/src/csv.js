// Export drafts to a review-friendly CSV that opens cleanly in Excel/Sheets
// and can be adapted for eBay Seller Hub bulk upload or crosslisters like Flyp.

const COLUMNS = [
  "Item",
  "Title",
  "Condition",
  "Category",
  "Brand",
  "Suggested Price",
  "Price Low",
  "Price High",
  "Item Specifics",
  "Flaws",
  "Keywords",
  "Description",
  "Verify Before Publishing",
  "Photos",
];

function cell(value) {
  const s = String(value ?? "");
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function draftsToCsv(drafts) {
  const rows = [COLUMNS.map(cell).join(",")];
  for (const { item, draft } of drafts) {
    rows.push(
      [
        item,
        draft.title,
        draft.condition,
        draft.category,
        draft.brand,
        draft.price.suggested,
        draft.price.low,
        draft.price.high,
        draft.item_specifics.map((s) => `${s.name}: ${s.value}`).join("; "),
        draft.flaws.join("; "),
        draft.keywords.join(", "),
        draft.description,
        draft.confidence_notes,
        draft._meta.photos.join("; "),
      ]
        .map(cell)
        .join(","),
    );
  }
  return rows.join("\r\n") + "\r\n";
}
