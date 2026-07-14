# Business Notes — eBay Listing Automation

*Notes captured 2026-07-07.*

## Current operation

- Target throughput: **150 listings/week**, with photos taken 7 days a week.
- Workflow: photos → eBay auto-lister/auto-drafter (this project, in development) → crosslisting via **Flyp** (paid subscription, ~$9/month).
- Scaling plan: hire a few part-time helpers (a few hours per person per week) as listing volume grows.

## Product idea (future) — sell the tool itself

Turn the auto-lister/auto-drafter into a sellable product:

- **Mobile app + desktop app that sync with each other.**
- Cross-platform support:
  - Android (Google / Samsung / Pixel devices, e.g. Pixel 10 Pro XL)
  - iOS / iPadOS (iPhone, iPad, iPod touch)
  - macOS
  - Windows (Microsoft)
- Core value: take photos on the phone, drafts appear on the desktop (and vice versa), listings pushed to eBay and crosslisted automatically.
- Positioning: complements or replaces per-month crosslisting subscriptions like Flyp.

## Open questions / next steps

- [ ] Define MVP scope for the eBay auto-drafter (photo intake → draft listing).
- [ ] Decide sync architecture (cloud backend vs. peer sync) for the mobile/desktop product.
- [ ] Pricing model if sold (subscription vs. one-time).
