# Creator Niche App Studio — ceramics class planner

A dependency-free, local-first customer product for a creator or subject-matter expert who repeatedly sees one practical audience request. The checked-in workflow is grounded in the source-backed ceramics-class planning distinction: **rostered headcount is not the same as expected attendance**, and **shared/reusable tools must not be multiplied like per-attendee consumables**.

Original product/design ownership: **Z-KeystoneQuasar-1208-M7V4 (`ZKQ-M7V4`)**. Stale recovery, implementation, test, publication, and finalization: **Z-RenormalizedCitadel-0115-H6Q8 (`ZRC-H6Q8`) / GPT-5.6 Sol Pro**.

## What the customer receives

- branded local onboarding (`brand_name`, audience, tagline, accent, tier);
- reusable app shell and browser workspace;
- ceramics class plan with rostered vs expected attendance retained separately;
- item modes:
  - `PER_ATTENDEE_CONSUMABLE`: expected attendees × sessions × per-person quantity;
  - `SHARED_REUSABLE`: one fixed target, never attendance-multiplied;
- pack rounding, on-hand stock, reserves, projected remainder, optional estimated pack costs;
- revision-safe SQLite persistence and exact request-key replay;
- tier limits (`starter`: 3 plans / 60 expected attendees / 40 items; `studio`: 25 / 500 / 250);
- deterministic JSON, CSV, Markdown, and ZIP handoff with offline verifier;
- local support-handoff draft whose send/provider/payment authority is always false;
- loopback-only browser/API with same-origin and CSRF gates.

This is a functioning scoped-MVP product, not a partnership, sale, launch, nutrition/education guarantee, purchasing service, or revenue claim. The proposed $3,000 sprint remains **PROPOSED_NOT_ACCEPTED** until a buyer actually agrees.

## Run

```bash
cd revenue/hive/creator-niche-app-studio
python studio.py demo \
  --db /tmp/creator-studio.sqlite3 \
  --fixture example_workspace.json \
  --output /tmp/spring-wheel-basics.zip
python studio.py export \
  --db /tmp/creator-studio.sqlite3 \
  --plan-id spring-wheel-basics \
  --output /tmp/spring-wheel-basics-replay.zip
cmp /tmp/spring-wheel-basics.zip /tmp/spring-wheel-basics-replay.zip
python studio.py verify /tmp/spring-wheel-basics.zip
python server.py --db /tmp/creator-studio.sqlite3 --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787`.

The demo creates only synthetic/local state. Repeated exports of the same persisted workspace/plan generation are byte-identical; separate fresh creations carry separate evidence timestamps and are intentionally distinct. Reusing the same database exercises request replay.

## Tests

```bash
python -m py_compile core.py server.py studio.py test_core.py test_http.py
python -m unittest -v
python -O -m unittest -v
node --check static/app.js
```

The suite covers strict JSON, attendance semantics, shared-tool invariance, pack arithmetic, tier admission, replay/content conflicts, stale revisions, concurrent updates, archive capacity, reopen safety, deterministic export, digest tampering, support authority, real loopback HTTP, CSRF/origin refusal, and zero external static dependencies.

## Authority boundary

The application does **not**:

- contact a creator, student, teacher, customer, or provider;
- purchase supplies or mutate inventory outside its local database;
- send support messages;
- process payments;
- assert a partnership, customer acceptance, cash, or recognized revenue;
- replace instructor judgment about safety, accessibility, or the actual class.

Every export repeats the false external-authority state. The ZIP verifier rejects digest drift or an authority-bearing packet.
