# ChartTrace Workbench

Demand ID: `charttrace-medical-evidence-review-01`  
State: **SYNTHETIC BUILD-AND-VERIFY**. Real records / family pilot: **HOLD**.  
Signing: **unsigned** synthetic artifact. `release_authorized=false`.

ChartTrace is a Windows-first standalone evidence workbench. It is not a GitHub Pages door, browser tab, public upload surface, or phone-download HTML file. There is no `doors/charttrace-medical-evidence-review.html`.

> ChartTrace is an investigative research aid. It separates record-supported observations, external authority, hypotheses, counterevidence, and professional review questions. Licensed counsel determines legal significance; qualified clinicians determine clinical significance.

This tree is assembled from collision-safe lanes. Do not treat an individual lane PR as a production installer, HIPAA certification, counsel approval, or Stripe integration.

## Lanes

| Lane | Owner seat | Paths |
| --- | --- | --- |
| A | CURSOR-GPT-A | `charttrace/core/**`, `charttrace/schema/**`, `charttrace/storage/**` |
| B | CURSOR-GROK-B | `charttrace/peers/**`, `charttrace/prompts/**`, `charttrace/grounding/**` |
| C | CURSOR-GPT-C | `charttrace/app/**`, `charttrace/ui/**`, `charttrace/legal/**`, `charttrace/packaging/**`, `charttrace/launcher.py` |
| D | CURSOR-GROK-D | `charttrace/review/**`, `charttrace/export/**`, `charttrace/counsel/**` |
| E | CURSOR-GEMINI-E | `charttrace/commercial/**`, `charttrace/pricing/**`, `charttrace/affiliates/**` |
| F | CURSOR-LEAD | `charttrace/fixtures/**`, `charttrace/assurance/**`, `test_charttrace_*.py` |
| Integrator | CURSOR-LEAD | `charttrace/__init__.py`, `charttrace/README.md`, `p/charttrace-medical-evidence-review-01.md` |

## Run (synthetic)

Lane tests are declared on each ACCEPT. After merge, from a checkout that contains F:

```bash
python3 -m unittest -v test_charttrace_assurance.py test_charttrace_language.py
```

Launch (after lane C lands): `python3 charttrace/launcher.py` — native window, no public TCP, persistent Legal / Data / Terms.

## Hard holds

No PHI in git, Slack, logs, fixtures, or exports. No external model calls. No outreach. No public deployment. No Stripe mutation, Connect, live routing, spend, or Cheri/Billings action. No force-push. Root merges.
