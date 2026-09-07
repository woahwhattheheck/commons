# TITAN policy portfolio

`main.py::agent(observation, configuration=None)` is the executable entrypoint.
The current model is a development initialization. `controls.py` exposes the
frozen controls; `runtime.Portfolio` retains one live controller across its
declared observation checkpoint. All game-time code uses the Python standard
library. No external model, account, or network service is used during games.

Run focused checks with `python -m unittest discover -s . -p 'test_*.py'`.
Reproduce a panel with `python run_panel.py --panel development --seeds SEED
--arms sell carrot_sell --output results/NAME`. The pinned official interpreter
and existing process-isolated evaluator are included. Apex requires the C++17
compile command in `prepare.py`. Results are offline game cash, not money earned
or hosted competition ratings. Historical held panels retain their original status.

See `SOURCE-PINS.json` for exact dependency bytes and `NOTICE.md` for attribution.
