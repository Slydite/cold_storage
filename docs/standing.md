# Standing decisions — Cold Storage Management System

Answers to design questions the agent should not need to re-ask. If a genuinely new ambiguity comes up that isn't covered here, default to whatever is most consistent with these patterns rather than inventing something new — consistency across modules matters more than any single "best" answer.

---

## 1. GRN & DN status lifecycle
- **DN mirrors GRN:** both have `DRAFT → POSTED`, plus `CANCELLED`.
- Stock only moves on `DRAFT → POSTED` transition (GRN creates lot stock on posting, DN withdraws on posting). A DRAFT record has zero stock impact and can be freely edited.
- **`CANCELLED` is only reachable from `DRAFT`.** A `POSTED` record cannot be cancelled directly — if a posted GRN/DN needs reversal, a corrective/reversal entry should be created instead (deferred: full reversal flow not required in v1, but never silently allow editing a posted record's quantities).
- Each status transition uses the same `select_for_update()` + service-layer pattern as everything else touching stock.

## 2. Lot lifecycle
- A Lot's status is derived, not manually set: `ACTIVE` while `remaining_qty > 0`, `CONSUMED` when it hits 0. No separate manual status field.
- One GRN line = one Lot. A DN line references exactly one Lot; a single DN can have multiple lines across multiple lots (confirmed from the paper delivery challan reference).

## 3. Weight shrinkage / loss tracking
- **Not implemented in v1.** `remaining_qty` reflects only GRN-in minus DN-out, no automatic decay model. This is a known limitation, not an oversight — flag it in the reports module so a manual "adjustment" entry type can be added later without restructuring the ledger.

## 4. Chambers / racks
- Model `Chamber` as a flat field on the facility (matches mockup: "Chamber A/B/C" dropdown) — no rack/floor sub-hierarchy in v1. Keep the Lot model's chamber reference as a simple FK so a rack sub-level can be added later without breaking existing data.

## 5. Items / products
- Items are a **master table** (`Item`: name, category, default packaging, default unit), referenced by FK from GRN/DN lines — not free-text per line. This is what makes stock reporting and rent-rate lookup by item category actually work. Seed it with the items visible in the reference documents (peas, sweet corn, cauliflower, etc.) plus an "add new item" flow for others.

## 6. Party model
- Single `Party` model serves both GRN suppliers and DN customers (same entity in practice — a party stores goods, then later withdraws them). GSTIN and mobile are **optional** fields (confirmed from the paper GRN — often left blank for small farmers).

## 7. Billing / rent calculation
- Rate card keyed by **item category × bag weight category** (20kg/50kg, per the paper GRN's rate table), rate expressed as ₹ per bag per month.
- Billing cycle: **monthly**, triggered manually via the "Rent Run" quick action (matches dashboard mockup) rather than fully automated on a cron — keep a human in the loop for v1 since rent runs touch money.
- Partial months: **prorate by days stored** (days_in_storage / days_in_month × monthly_rate) rather than rounding to full months — simpler to explain to customers and matches how the paper form's "per nag/maah" rate implies daily granularity is expected.
- Loading/unloading labor charge is a **one-time charge at GRN time**, separate line item from recurring rent — not folded into the monthly rate.

## 8. GST invoicing
- Triggered manually via "Generate Invoice" quick action, typically after a Rent Run — not auto-generated on every DN (matches the earlier finding that "only an invoice is created," separate from GRN/DN, which don't themselves carry GST).
- Invoice numbering is its own sequential, gapless-per-financial-year counter, independent of GRN/DN numbering (per §2.4 of the main spec).
- E-invoicing (IRN/GSP integration) stays out of scope until turnover threshold makes it mandatory — do not build this speculatively.

## 9. Auth / users / RBAC
- Single `role` field on the user model, only value in use today is `admin`. No permission-check branching logic yet — just the field existing, so RBAC is additive later.
- Seed one admin user via `createsuperuser`; no self-registration flow needed for an in-house tool.

## 10. Facility / multi-tenancy
- One `Facility` row exists (seed it: "Main Cold Storage," matching the mockup's facility switcher label). Every model still carries `facility_id` per the spec, but there's no facility-switching logic to build yet beyond the field existing.

## 11. File storage (PDFs, exports)
- Local filesystem (Django `MEDIA_ROOT`) is sufficient for v1, no S3/object storage needed at in-house scale. Revisit only if deployment moves off a single VPS.

## 12. Numbering formats (to match the mockups exactly)
- GRN: `GRN-000123` · DN: `DN-000089` · Invoice: `INV-000256` · Lot: `LOT-000086` — zero-padded 6-digit sequential, prefix per document type, each its own counter.

## 13. What "done" looks like per module
For each module (GRN, Delivery, Billing, Invoicing), autonomous build should include: model + migration, service functions, serializers, ViewSet + routes registered, Django admin registration, tests covering the service layer (especially anything touching stock or money), and the corresponding Vue list view + create/edit split-panel per the UI spec. A module isn't complete until all of these exist — not just the API.

---

If the agent hits a decision not covered above, prefer: matching an existing pattern in this doc > matching the mockups > asking. Only stop and ask if the answer would be genuinely irreversible or expensive to change later (e.g. a schema decision affecting every table) — implementation-detail questions should default sensibly and note the assumption in the PR/response.