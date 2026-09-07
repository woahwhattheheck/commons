# T11 provenance and scope

`candidate.py`, `cycle.py`, and the tests are MIT-licensed T11 work. The
runtime composes the frozen T08 SELL entrypoint and its pinned Apache-2.0
mechanics helper without modifying those files. Their original notices remain
under `cloud-titan-composition/vendor/sell/`.

The official interpreter is used only by tests and the offline evaluator. No
private opponent source, hosted replay state, credentials, or Kaggle writes are
runtime inputs.
