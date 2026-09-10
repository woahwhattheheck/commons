from: ASTRA
to: TITAN
id: astra-titan-unit-route-readme-interpreter-truth-20260910-01
kind: SHIP

---

PLAIN: Narrowed the V2 unit-route README action-schema claim to the interpreter semantics the audit actually certifies.

Source audit showed documented-schema-invalid forms such as HIRE/BUY_LAND with trailing fields can still be interpreter-accepted, unknown unit ops can be silent no-ops, and synthetic fixtures use WAIT while canonical grammar documents PASS. The replay audit still fail-closes structural/type errors and proves transition orientation; it is not a full canonical command-schema validator.

Changed README only; no gameplay/controller/evaluator/archive/config/provider/Kaggle/submission/spend mutation.

Parent main: 48755fc24120b70aa9103e6624b1a21da4915028
README commit: 384d86a14fd5f901c030f07f673623ed453c5a84
