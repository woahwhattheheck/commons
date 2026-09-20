# CUA-S1-FORMS choice scoring

`host/cua_s1_forms.py` exposes the published [CUA-S1-FORMS](https://huggingface.co/cua-ai/cua-s1-forms) checkpoint as a local JSON choice scorer. It does not control a browser, call Cua Driver, or submit a form. Use its output as a proposed choice and verify the target and outcome before acting.

The upstream [source package](https://github.com/trycua/cua/tree/main/libs/cua-s1) requires Python 3.11–3.13, PyTorch, NumPy, and safetensors. Install `cua-s1` from that package and download the matching `cua-s1-forms.safetensors` and `cua-s1-forms.json` files from the model repository. The upstream loader checks the checkpoint format and tensor signature. The source and published checkpoint carry MIT licenses. This path uses no `llama.cpp` runtime or dependency.

Example input, saved as `request.json`:

```json
{
  "context": "TASK fill the form from the document, then submit\nFORM Northwind Clinic - New Patient Registration\nELEMENT Edit \"Phone number\" value=\"\"\n",
  "options": ["fill Tel: (503) 555-0142", "fill DOB: 03/14/1987", "check", "click", "skip"]
}
```

Run with the local checkpoint and matching JSON sidecar:

```powershell
python host/cua_s1_forms.py --checkpoint C:\path\to\cua-s1-forms.safetensors --input request.json
```

Output contains the selected index, one probability per option, the actual device, and `"executed": false`. The source model truncates context to 224 UTF-8 bytes and each option to 96 bytes; keep the element context concise. The model only chooses from supplied options. Its published evaluation includes three real demo forms and three PDFs, so wider reliability has not been established. [Model card](https://huggingface.co/cua-ai/cua-s1-forms) and [upstream scope and safety guidance](https://github.com/trycua/cua/blob/main/libs/cua-s1/MODEL_CARD.md) govern use.

On this Windows CPU, the published checkpoint chose the phone number option in the example above with probability 0.99998. A second probe using `ELEMENT CheckBox "I agree to terms" checked=false` chose `skip` with probability 1.0, even though `check` was offered. These are observations on two inputs, not a reliability estimate; inspect each proposal before using it.

CUA-S1's optional Cua Driver planner has a separate execution contract. Its [README](https://github.com/trycua/cua/blob/main/libs/cua-s1/README.md) says the portable driver contract does not currently expose `set_value`, so filling through that path fails closed without a compatible token-based mutation implementation. This local scorer leaves that interface untouched.
