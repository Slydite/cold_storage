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

## 4. Location hierarchy
- **CORRECTED (2026-07-27), supersedes all earlier versions of this section.** The owner (who runs the business) confirmed the real hierarchy is **Facility → Chamber → Floor → Block**. Two earlier readings were wrong: v1 had a flat chamber field, and the 2026-07-25 revision had Floor above Chamber. What the code previously called a "Chamber" is in fact a **Block**; a Chamber is the level *above* Floor.
- `Chamber`, `Floor` and `Block` are real master tables in `apps.locations`: `Chamber` belongs to a Facility, `Floor` to a Chamber, `Block` to a Floor. All three are managed from the Settings page, and pickers cascade (choosing a chamber narrows floors, choosing a floor narrows blocks).
- The rename was done with a hand-written migration (`locations/0002_restructure_hierarchy`) rather than the autodetector's diff, which emitted a destructive drop/recreate. On SQLite, `AlterUniqueTogether(→ set())` must come **before** the `RemoveField` or the table remake fails — check ordering by hand whenever this hierarchy changes again.
- `Lot` carries `chamber_ref`/`floor_ref`/`block_ref` FKs **alongside** the legacy free-text `floor`/`chamber`/`rack` columns. The text columns are retained only until every row is verified backfilled, then a later change drops them. **Nothing may filter or match on them** — new code reads the FKs, and reads `location_display` for presentation. A filter comparing against the free-text column silently returns nothing, which is how a dead chamber filter survived unnoticed on the GRN list.
- Racks remain unmodelled. Add a `Rack` under `Block` when the business actually needs it.

## 5. Items / products
- Items are a **master table** — the model is called **`Commodity`** (in `apps.commodities`), not `Item`; earlier drafts of this doc used the wrong name. Referenced by FK from GRN/DN lines, never free-text per line. Carries a default unit, which pre-fills the GRN line's `unit` but can be overridden per line.
- Seeded with the produce visible in the reference documents (potato, peas, sweet corn, cauliflower, carrot, chilli, ginger, garlic…), plus an "add new commodity" flow from Settings.

## 6. Party model
- Single `Party` model serves both GRN suppliers and DN customers (same entity in practice — a party stores goods, then later withdraws them). GSTIN and mobile are **optional** fields (confirmed from the paper GRN — often left blank for small farmers).

## 7. Billing / rent calculation
- **REWRITTEN (2026-07-27), supersedes all earlier versions of this section.** Rate Cards and Rent Runs were **deleted outright** — models, endpoints, UI and the periodic-billing concept. Do not reintroduce them. Everything below came directly from the owner.
- **The GRN line is the only source of rate truth.** Each lot line carries `rent_rate_per_unit`, the negotiated ₹ per unit per month, entered at intake. Rates are negotiated per customer and per commodity, so there is no list rate to resolve against and no rate table to look up.
- **Unit is per line** (BAGS / BOXES / CRATES …), defaulted from the commodity but overridable — the business stores different packagings of the same commodity.
- **Slab billing, not proration.** Minimum 30 days from GRN creation, then 15-day slabs: 30, 45, 60, 75 … The multiplier is `1.0` for `days ≤ 30`, else `1 + 0.5 × ceil((days − 30) / 15)`. The owner's worked example is binding: 100 bags at ₹12 for 34 days = `100 × 12 × 1.5 = ₹1800.00`. Verified multipliers: 30→1.0, 31→1.5, 45→1.5, 46→2.0, 60→2.0, 61→2.5. This replaces the old prorate-by-days rule entirely.
- **Only withdrawn stock is billable.** Goods still in storage simply accrue; rent is charged when stock leaves on a posted Delivery Note. Each delivery line is billed exactly once, enforced by `DeliveryLine.invoiced_at` + the `invoice_line` FK.
- **Both documents carry a labour/transport charge**, each with a `FLAT` / `PER_UNIT` mode and a server-computed `computed_loading_charge`. Call it a **Receiving Charge** on a GRN and a **Delivery Charge** on a DN — never "loading/unloading", which is ambiguous because both events physically involve both. Each is billed once, on the first invoice that includes any withdrawal from that document.
- **A GRN must never display a rent total or any computed amount.** The owner is explicit: a GRN is an intake record and cannot know the amount beyond the agreed rate and the charge. Quantity subtotals are fine; money totals are not.
- `apps.billing.services` is now a **pure calculator with no models** — `billable_multiplier`, `days_stored`, `compute_line_rent`, `compute_delivery_line_rent`. Money is Decimal-only with `ROUND_HALF_UP`.

## 8. GST invoicing
- **UPDATED (2026-07-27).** Triggered manually via "Generate Invoice", scoped to a **party's uninvoiced withdrawals** — there is no Rent Run to follow any more. Typically raised when a lot runs out, but the owner can raise one earlier for partial completeness, so partial invoicing of a lot must always work.
- **Always preview before generating.** `GET /api/invoices/preview/` returns the per-party line breakdown and server-computed totals without writing anything: it creates no rows, never sets `invoiced_at`, and must never consume an invoice sequence number. Preview and generation share one pure `build_invoice_items()` so the two cannot drift — if you change the calculation, change it there and nowhere else. The UI disables Generate while the preview is loading, errored or empty.
- **Payments are tracked.** `Payment` rows hang off an invoice (FK `PROTECT`); `amount_paid` / `amount_due` / `payment_status` (`UNPAID` / `PARTIAL` / `PAID`) are **derived server-side** and clamp at zero on overpayment. Clients display these values and never compute money themselves.
- Invoice numbering is its own sequential, gapless-per-financial-year counter, independent of GRN/DN numbering (per §2.4 of the main spec).
- E-invoicing (IRN/GSP integration) stays out of scope until turnover threshold makes it mandatory — do not build this speculatively.

## 9. Auth / users / RBAC
- Single `role` field on the user model, only value in use today is `admin`. No permission-check branching logic yet — just the field existing, so RBAC is additive later.
- Seed one admin user via `createsuperuser`; no self-registration flow needed for an in-house tool.
- User management (list/create/update/activate/deactivate) exists from the Settings page. Two constraints worth keeping: deactivating the **last active admin is refused** (unrecoverable lockout in an in-house tool), and `is_active` is **not** accepted by the update endpoint — activation changes only through the explicit activate/deactivate actions, because DRF's `BooleanField` coerces an absent value to `False` on form input and a plain rename was silently deactivating accounts.
- **Open caveat:** user-management endpoints sit behind plain `IsAuthenticated`, like everything else. That is acceptable while `admin` is the only role, but must be revisited the moment a second role exists.

## 10. Facility / multi-tenancy
- **UPDATED (2026-07-25).** Multiple facilities are now supported and manageable from Settings. The sidebar switcher picks the *working* facility used for creating GRNs/DNs/parties/locations; Inventory has its own independent filter that can additionally show stock **across all cold storages** at once. The two are deliberately separate — viewing everything shouldn't change what you're currently working in.
- Facility carries the identity data its printed documents need: GSTIN, office and factory phones, bank account + IFSC, and editable terms text (taken from the real receipt letterhead).

## 11. File storage (PDFs, exports)
- Local filesystem (Django `MEDIA_ROOT`) is sufficient for v1, no S3/object storage needed at in-house scale. Revisit only if deployment moves off a single VPS.

## 12. Identifiers, numbering and input sanitisation
- Zero-padded 6-digit sequential, one counter per type: GRN `GRN-000123` · DN `DN-000089` · Invoice `INV-000256` · Lot `LOT-000086` · Party `PRT-000001` · Commodity `CMD-…` · Chamber `CHM-…` · Floor `FLR-…` · Block `BLK-…` · Facility `FAC-…`.
- **Every identifier is generated server-side, on every entity that can be created (2026-07-27, owner's instruction: "auto generation should be on every field that involves creating a new thing").** Input serializers do **not** accept a `code`/number — a client-supplied one is ignored, not honoured. Create forms must therefore show no code input; the generated value appears read-only in tables and detail views afterwards.
- Sequences are allocated under `select_for_update()` inside the creating transaction. Read-only paths must never call `get_next_sequence_number` — doing so burns numbers (this is why invoice preview is strictly read-only).
- **All free text is sanitised in the service layer**, never in views or serializers: `libs/sanitizers.py` provides `clean_text`, `title_name`, `upper_code`, `clean_gstin`, `clean_phone`, `clean_email`. `title_name` deliberately preserves existing intra-word capitalisation ("GD Foods" stays "GD Foods", "o'brien" → "O'Brien"); `clean_phone` must not merge separate digit groups.

## 13. What "done" looks like per module
For each module (GRN, Delivery, Billing, Invoicing), autonomous build should include: model + migration, service functions, serializers, ViewSet + routes registered, Django admin registration, tests covering the service layer (especially anything touching stock or money), and the corresponding Vue list view + create/edit split-panel per the UI spec. A module isn't complete until all of these exist — not just the API.

---

If the agent hits a decision not covered above, prefer: matching an existing pattern in this doc > matching the mockups > asking. Only stop and ask if the answer would be genuinely irreversible or expensive to change later (e.g. a schema decision affecting every table) — implementation-detail questions should default sensibly and note the assumption in the PR/response.