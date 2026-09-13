# Mixed resource planner — source-backed Hive016 follow-through

Open `resource_planner.html` directly in a browser. It is a local-only workshop planner for a workflow the Hive016 research actually supported: a creator/teacher may distinguish **rostered headcount** from **expected attendance** while planning a mix of **shared/reusable tools** and **per-attendee consumables**.

## Semantics

- `Rostered headcount` is retained as planning context and never drives quantities.
- `Expected attendees` multiplies only resources in `Per attendee consumable` mode.
- `Shared / reusable` quantity is fixed for the workshop and is invariant when attendance changes.
- Reserve percentage and whole-pack rounding apply to both modes.
- The example quantities are editable planning examples. They are not copied from the creator source and are not procurement recommendations.

The app saves named plans in browser local storage, reopens them, exports the current plan as CSV, and exports/restores saved plans as JSON. It performs no network requests and has no checkout, messaging, tracking, inventory inference, or pricing integration.

## Acceptance fixture

With rostered headcount `35`, expected attendees `28`, a shared resource quantity of `4`, and a per-attendee consumable quantity of `1.5` in packs of `10`:

- changing expected attendance from 28 to 35 keeps the shared requirement at `4`;
- the consumable requirement changes from `42` (5 packs / 50 units purchased) to `52.5` (6 packs / 60 purchased);
- changing rostered headcount alone changes neither calculation.

Run the focused contract:

```sh
python -B -m unittest -v test_resource_planner.py
```

This is a product-fit extension of the already-shipped Hive016 studio, not evidence of a buyer, partnership, sale, or creator request for this specific software.
