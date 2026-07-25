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

## 4. Chambers / floors / racks
- **SUPERSEDED (2026-07-25).** The original v1 decision was a flat chamber field with no floor level. The owner has since confirmed the real hierarchy is **Cold Storage (building) → Floor → Chamber**, with room left for multi-tenancy and richer accounts later. The business's own paper GRN confirms it — its remarks field reads "मंजिल-2 कक्ष-4" (Floor 2, Chamber 4).
- `Floor` and `Chamber` are now real master tables in `apps.locations`: `Floor` belongs to a Facility, `Chamber` belongs to a Floor. Both are managed from the Settings page.
- `Lot` carries `floor_ref`/`chamber_ref` FKs **alongside** the legacy free-text `floor`/`chamber`/`rack` columns. This is a deliberate two-phase migration: the text columns stay until every row is verified backfilled, then a later change drops them. Lots that had a chamber but no floor (from the flat era) were parented to a per-facility "Ground Floor" placeholder rather than losing their location.
- Racks remain unmodelled. Add a `Rack` under `Chamber` when the business actually needs it.

## 5. Items / products
- Items are a **master table** (`Item`: name, category, default packaging, default unit), referenced by FK from GRN/DN lines — not free-text per line. This is what makes stock reporting and rent-rate lookup by item category actually work. Seed it with the items visible in the reference documents (peas, sweet corn, cauliflower, etc.) plus an "add new item" flow for others.

## 6. Party model
- Single `Party` model serves both GRN suppliers and DN customers (same entity in practice — a party stores goods, then later withdraws them). GSTIN and mobile are **optional** fields (confirmed from the paper GRN — often left blank for small farmers).

## 7. Billing / rent calculation
- Rate card keyed by **item category × bag weight category** (20kg/50kg, per the paper GRN's rate table), rate expressed as ₹ per bag per month.
- Billing cycle: **monthly**, triggered manually via the "Rent Run" quick action (matches dashboard mockup) rather than fully automated on a cron — keep a human in the loop for v1 since rent runs touch money.
- Partial months: **prorate by days stored** (days_in_storage / days_in_month × monthly_rate) rather than rounding to full months — simpler to explain to customers and matches how the paper form's "per nag/maah" rate implies daily granularity is expected.
- Loading/unloading labor charge is a **one-time charge at GRN time**, separate line item from recurring rent — not folded into the monthly rate.
- **Rates are per-party, not just per-commodity (added 2026-07-25).** `RateCard` carries an optional `party`: a card with no party is the default/list rate for everyone; a card with a party is a negotiated override. Resolution is **specificity over recency** — a party's rate wins even when a newer default exists. Both dimensions still respect `effective_from`, so a party's own newer rate supersedes their older one.
- A GRN also records the preservation rate agreed at intake (it is written on the paper receipt). That field is **documentary only** — billing always resolves rates from `RateCard`, so there is never a second source of truth for money.
- Rent runs take more than a date range: optional party / commodity / chamber narrowing, a `min_billing_days` floor for minimum-stay terms, and free-text notes. A **preview** endpoint dry-runs a period without persisting, reporting which rate applied to each line (`PARTY` vs `DEFAULT`) and listing lots with no applicable rate card instead of failing — the operator sees what is blocking the run and can fix it before committing.

## 8. GST invoicing
- Triggered manually via "Generate Invoice" quick action, typically after a Rent Run — not auto-generated on every DN (matches the earlier finding that "only an invoice is created," separate from GRN/DN, which don't themselves carry GST).
- Invoice numbering is its own sequential, gapless-per-financial-year counter, independent of GRN/DN numbering (per §2.4 of the main spec).
- E-invoicing (IRN/GSP integration) stays out of scope until turnover threshold makes it mandatory — do not build this speculatively.

## 9. Auth / users / RBAC
- Single `role` field on the user model, only value in use today is `admin`. No permission-check branching logic yet — just the field existing, so RBAC is additive later.
- Seed one admin user via `createsuperuser`; no self-registration flow needed for an in-house tool.
- User management (list/create/update/activate/deactivate) exists from the Settings page. Two constraints worth keeping: deactivating the **last active admin is refused** (unrecoverable lockout in an in-house tool), and `is_active` is **not** accepted by the update endpoint — activation changes only through the explicit activate/deactivate actions, because DRF's `BooleanField` coerces an absent value to `False` on form input and a plain rename was silently deactivating accounts.
- **Open caveat:** user-management endpoints sit behind plain `IsAuthenticated`, like everything else. That is acceptable while `admin` is the only role, but must be revisited the moment a second role exists.

## 10. Facility / multi-tenancy
- **UPDATED (2026-07-25).** Multiple facilities are now supported and manageable from Settings. The sidebar switcher picks the *working* facility used for creating GRNs/DNs/parties/rate cards; Inventory has its own independent filter that can additionally show stock **across all cold storages** at once. The two are deliberately separate — viewing everything shouldn't change what you're currently working in.
- Facility carries the identity data its printed documents need: GSTIN, office and factory phones, bank account + IFSC, and editable terms text (taken from the real receipt letterhead).

## 11. File storage (PDFs, exports)
- Local filesystem (Django `MEDIA_ROOT`) is sufficient for v1, no S3/object storage needed at in-house scale. Revisit only if deployment moves off a single VPS.

## 12. Numbering formats (to match the mockups exactly)
- GRN: `GRN-000123` · DN: `DN-000089` · Invoice: `INV-000256` · Lot: `LOT-000086` — zero-padded 6-digit sequential, prefix per document type, each its own counter.

## 13. What "done" looks like per module
For each module (GRN, Delivery, Billing, Invoicing), autonomous build should include: model + migration, service functions, serializers, ViewSet + routes registered, Django admin registration, tests covering the service layer (especially anything touching stock or money), and the corresponding Vue list view + create/edit split-panel per the UI spec. A module isn't complete until all of these exist — not just the API.

---

If the agent hits a decision not covered above, prefer: matching an existing pattern in this doc > matching the mockups > asking. Only stop and ask if the answer would be genuinely irreversible or expensive to change later (e.g. a schema decision affecting every table) — implementation-detail questions should default sensibly and note the assumption in the PR/response.