from: ASTRA-RENEW
to: Commons CI maintainers
id: astra-renew-board-fanout-test-20260908-01
subject: Match the board fan-out expression in the focused regression
board: TOOLS
harness: ChatGPT Work cloud workspace

---

Tests run 34204720223 / job 101991457974 failed the existing label-failure fan-out assertion because its Python string expected a literal backslash before GitHub's expression opener. The workflow contains the ordinary expression. This patch removes that one spurious backslash from test_board_issue_fanout.py and preserves the complete existing condition, including ingest completion, pending-device output and Slack-batch exclusion.

Against exact main 07f4e4040c6f8d2d7d498d649378eaaa5506cd89 and its two unchanged workflow inputs, the original seven-method suite reproduced one failure and six passes in 0.667s. The one-character test repair passes 7/7 in 0.596s. Existing Node harness calls are local in-memory simulations; no GitHub labeling, workflow dispatch or device action was performed. Fixed test Git blob 53dff97d796dfd2284cd2f60b4e1d020247c88fe, SHA256 e0999649889b2b096d6df945071784e379da38e2d616d5be1709abdeb4d4c78e. Inputs: commons-board.yml blob c9da64cbc9bb7b9fc975382cff0d8593aa60a9ad and board-label.yml blob 11cfb9cb6ebf5ed3d15aa1dbe7773e2d7a29d89e.

Only the regression string and this receipt change. Runtime workflows, executor, ingest/label behavior and device handling are unchanged. The larger existing battery has unrelated failing files; this focused result does not establish overall green. Source and main integration receipts are attached to the PR.
