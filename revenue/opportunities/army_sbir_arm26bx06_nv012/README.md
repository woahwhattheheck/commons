# Army SBIR ARM26BX06-NV012 — decision-program Phase I carrier

Internal qualification and proof-by-demonstration carrier for Commons issue #14279.

The first-party Army topic asks for schema-driven Decision Management plus governed agentic AI that produces auditable decision packages, explicit assumptions/risks/bias checks, reproducible evaluation and decision-flip logic, with two demonstrations spanning point studies and refreshable decision programs.

Source: https://armysbir.army.mil/topics/agentic-ai-schema-driven-decision-management/

## Run

```bash
python -B decision_program.py evaluate examples/point_trade.json
python -B decision_program.py evaluate examples/long_horizon_g1.json
python -B decision_program.py evaluate examples/long_horizon_g2.json
python -B decision_program.py verify-refresh examples/long_horizon_g1.json examples/long_horizon_g2.json
python -B qualification_gate.py qualification.example.json
python -B -m unittest discover -s tests -v
python -O -B -m unittest discover -s tests -v
```

The example qualification is expected to remain `HOLD`; that is a feature. No Army/DSIP contact, registration, proposal submission, certification, signature, price commitment, award claim or recognized revenue is authorized by this package.
