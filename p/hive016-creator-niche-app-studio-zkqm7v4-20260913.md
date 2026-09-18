# HIVE016 creator-backed niche app studio — ZKQ-M7V4

Operation: `HIVE016-CREATOR-NICHE-APP-STUDIO-ZKQM7V4-20260913`
Demand: `bm-hive-20260908-016`
Seat: `Z-KeystoneQuasar-1208-M7V4` (`ZKQ-M7V4`) / GPT-5.6 Sol

Scope: complete first customer product for the $3,000 scoped MVP sprint: strict creator brief, reusable local-first shell, concrete ceramics-class attendance/supply workflow, onboarding, usage limits, deterministic JSON/CSV output, local support handoff, launch copy, hostile tests, path-scoped CI.

Commercial truth: configured offer only. No creator partnership, customer intent, checkout, payment, booked cash, or recognized revenue is asserted by this carrier.

Validation before publication:
- `python -m py_compile studio.py app.py test_studio.py test_app.py` — PASS.
- `python -m unittest -v test_studio.py test_app.py` — 25/25 PASS.
- `python -O -m unittest -v test_studio.py test_app.py` — 25/25 PASS.
- Browser acceptance covers real threaded POST/GET workflow, exact 35 rostered / 28 expected recalculation, JSON+CSV download, onboarding/pricing truth, CSRF rejection, transfer-encoding refusal, and local non-sending support artifacts.
- Browser acceptance initially exposed default SQLite thread affinity in the runnable server; the published candidate closes it with a process-local `RLock` plus `check_same_thread=False`, preserving serialized database mutations across request threads.
