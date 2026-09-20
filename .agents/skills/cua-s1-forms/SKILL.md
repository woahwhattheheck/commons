---
name: cua-s1-forms
description: Score candidate values and actions for a form element with the published CUA-S1-FORMS checkpoint. Use for bounded form choice analysis when the source document has already been parsed into candidate entities.
---

# CUA-S1-FORMS in Commons

Run `python host/cua_s1_forms.py --checkpoint <cua-s1-forms.safetensors> --input <request.json>` from the Commons root. The matching `cua-s1-forms.json` sidecar must be next to the safetensors file. Without `--input`, the command reads one JSON request from stdin. See [the integration guide](../../../host/CUA_S1_FORMS.md) for the request and output format.

Install the upstream `cua-s1` Python package from `https://github.com/trycua/cua/tree/main/libs/cua-s1/python` with its declared Python, PyTorch, NumPy, and safetensors requirements. Download both checkpoint files from `https://huggingface.co/cua-ai/cua-s1-forms`. Review upstream revision and package dependencies before installing. The published model uses PyTorch and safetensors; this skill does not use `llama.cpp`.

Supply the exact form element context and explicit options. The model chooses only among those options and returns their probabilities. Treat the selected index as a proposed decision. Inspect the form state and confirm outcomes independently. This command never performs form actions and always returns `executed: false`.

The published model is a narrow research checkpoint trained on synthetic forms with a small real-demo evaluation. It does not establish reliability on arbitrary production forms. The optional Cua Driver planner is a separate integration; its current portable contract does not expose `set_value`, so automatic fill execution through that path fails closed unless a compatible token-based mutation backend is available. Do not infer that scoring itself executed or submitted anything.
