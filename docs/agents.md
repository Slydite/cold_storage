# Project conventions — Cold Storage Management System

Read this before writing any code. Follow it even when not explicitly reminded in a prompt.

## Stack
- Backend: Django + DRF, PostgreSQL, apps under `backend/apps/`
- Frontend: Vue 3 + `<script setup>` + TypeScript, PrimeVue components, Pinia, TanStack Query `frontend/`
- Full spec: see `docs/cold-storage-system-spec.md`

## Backend rules

1. **Layering is mandatory, per app:**
   - `models.py` — data + DB constraints only, no business logic
   - `services.py` — all business logic. Views must call services, never contain logic themselves.
   - `serializers.py` — I/O validation only
   - `views.py` — thin: parse request → call service → serialize response
   - Put complex read queries in `selectors.py`, not in views or models

2. **Stock quantity is sacred.** Any lot withdrawal must use `select_for_update()` inside a transaction. Never allow `remaining_qty` to be set directly from client input — it is always derived server-side from ledger entries (GRN in, DN out).

3. **Sequence numbers** (GRN no., DN no., invoice no.) use the shared `Sequence` model + `select_for_update()` pattern in `libs/sequences.py`. Never use `Model.objects.count() + 1` or similar — it race-conditions and breaks on deletion.

4. **Every new model** that's financially or operationally significant (GRN, DN, Lot, Party, Invoice) gets `simple_history.HistoricalRecords()` for audit trail — add this by default, don't wait to be asked.

5. **Every viewset** gets an explicit `permission_classes` (default `IsAuthenticated`) even though RBAC isn't built yet — deny-by-default, additive later.

6. **Every new/changed API field** should regenerate the OpenAPI schema — remind the user to run `npm run gen:types` on the frontend after backend API changes.

7. **Tests are required** for anything in `services.py`, especially stock ledger math and rent/billing calculations. Don't skip tests to move faster on these specifically.

8. **Migrations** are always generated via `makemigrations`, never hand-written or hand-edited.

9. **`facility_id`** goes on every new model (FK, nullable=False, default to the single existing facility) — this is the multi-tenancy seam, don't skip it even though there's only one facility today.

## Frontend rules

1. **Business logic lives in `composables/`, not in `.vue` files.** A component should be template + light glue code. If a `.vue` file is approaching ~150 lines, extract logic to a composable or split the component.

2. **Use PrimeVue components, don't hand-build widgets** that the library already provides (tables, dropdowns, date pickers, dialogs, toasts). Custom CSS should be the exception, not the default.

3. **API calls live in `api/`** (one file per domain, e.g. `api/grn.ts`), typed against `types/api.ts` (generated from the backend OpenAPI schema — don't hand-write types that duplicate it).

4. **Data fetching goes through TanStack Query**, not raw `axios` calls scattered in components — this keeps loading/error/retry/cache behavior consistent across every screen.

5. **Every list/table view needs three explicit states**: loading (skeleton), empty (with a clear next action), and error (with a retry). Don't ship a screen with only the happy path.

6. **Every write action** (create/edit/delete) shows a toast confirmation or error — the person using this is doing data entry all day and needs unambiguous feedback.

7. **Forms use `vee-validate` + `zod` schemas**, shared between create and edit forms where the shape overlaps — don't duplicate validation logic per form.
   - This project runs **zod v4**, so `required_error` does not exist — use `.min(1, 'msg')`.
   - **Never use `.default()` in a schema passed to `toTypedSchema`.** `@vee-validate/zod` still targets zod v3, where `_def.defaultValue` is a function; in v4 it is a plain value, so `useForm()` throws `value._def.defaultValue is not a function` at setup and takes the whole render tree down with it — every screen, not just the offending form. Put defaults in `useForm({ initialValues })` instead.
   - Editable arrays/objects the template mutates with `v-model` must be plain `ref`s, never a `computed` over vee-validate's `values` — that silently wipes user input as they type.

8. **Responsive down to 375px width** — this app gets wrapped in a Flutter WebView later, so mobile-width usability isn't optional.

## Cross-cutting

- Don't introduce new dependencies (backend or frontend) without checking they're not already covered by something installed — no duplicate libraries solving the same problem.
- Don't add Celery, multi-tenant org-switching, or RBAC permission logic unless explicitly asked — these are deliberately deferred, see spec §4.4.
- When a task is ambiguous, follow the build order in the spec (`parties` → `inventory`/`grn` → `delivery` → `billing`/`invoicing` → `reports`) rather than guessing at scope.
- Keep a running note of any convention you deviate from and why — flag it in the PR/response so it can be reviewed, not silently baked in.