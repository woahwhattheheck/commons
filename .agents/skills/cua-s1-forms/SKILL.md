---
name: cua-s1-forms
description: Score candidate values and actions for a form element with the published CUA-S1-FORMS checkpoint, or plan and execute a bounded form workflow in an exact Chrome tab through direct CDP. The source document must already be parsed into candidate entities.
---

# CUA-S1-FORMS in Commons

Use the hosted Commons routes when the caller must continue while this laptop or Codex is offline. `POST https://commons-spark-mcp.vercel.app/cua-s1` takes `{"context":"...","options":["...","..."]}` and returns a model-selected index and per-option probabilities without browser action. The public Commons MCP tool is `cua_s1_score` with the same input. `POST https://commons-spark-mcp.vercel.app/cua-s1/form` takes an exact public `url`, `form_title`, and up to 29 `entities` of `{label,value}`. It runs an isolated cloud Chromium and previews by default; `execute:true` allows fill/check after a complete-plan preflight, and `submit:true` additionally allows one exact Submit click. Verify production availability through the live GET routes and a preview, as described in the [integration guide](../../../host/CUA_S1_FORMS.md).

Run `python host/cua_s1_forms.py --checkpoint <cua-s1-forms.safetensors> --input <request.json>` from the Commons root. The matching `cua-s1-forms.json` sidecar must be next to the safetensors file. Without `--input`, the command reads one JSON request from stdin. See [the integration guide](../../../host/CUA_S1_FORMS.md) for the request and output format.

Install the upstream `cua-s1` Python package from `https://github.com/trycua/cua/tree/main/libs/cua-s1/python` with its declared Python, PyTorch, NumPy, and safetensors requirements. Download both checkpoint files from `https://huggingface.co/cua-ai/cua-s1-forms`. Review upstream revision and package dependencies before installing. The published model uses PyTorch and safetensors; this skill does not use `llama.cpp`.

Supply the exact form element context and explicit options. The model chooses only among those options and returns their probabilities. Treat the selected index as a proposed decision. Inspect the form state and confirm outcomes independently. This command never performs form actions and always returns `executed: false`.

For an observed browser form, use `python -m host.cua_s1_run --url <exact-open-tab-url> --checkpoint <checkpoint> --input <form.json>` from the Commons root. `form.json` contains a `form_title` and an `entities` array of `{label,value}` objects. The default run previews decisions without action. Add `--execute` to fill/check, and `--submit` only to allow one recognized Submit click. The runner needs the optional `playwright` Python package and direct Chrome CDP endpoint; it never uses the Chrome extension. See [the integration guide](../../../host/CUA_S1_FORMS.md) for commands, boundaries and output.

Commons peers may also discover `cua_s1_form` through the existing shared equipment catalog. Pass the same exact open tab URL, form title, and entity array. The host resolves the official cached checkpoint by default; `execute` and `submit` are separate optional booleans. Read the returned plan and action observations before reporting an outcome.

The published model is a narrow research checkpoint trained on synthetic forms with a small real-demo evaluation. It does not establish reliability on arbitrary production forms. The portable Cua Driver contract lacks `set_value`, while this Chrome adapter supplies token-based value mutation and reads the result after each action. Do not infer that scoring alone executed or submitted anything.
