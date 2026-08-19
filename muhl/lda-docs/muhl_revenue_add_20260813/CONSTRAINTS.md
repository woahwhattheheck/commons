# Constraints for this pack (2026-08-13)

Additive era. These files exist so later sessions do not re-open the Claude cycle.

## Add only

- Create new files and new directories.
- Never modify or delete anything already on disk.
- Never git commit from this pack.
- Never write `titan.gguf`.
- Never write `titan_circuits.json`.
- Do not edit `CLAUDE.md`, README files, patents, or INDEX to “wire this in.”
- If a name collides, pick a new name. Do not overwrite.

## No osc

Do not cook the oscillator family. Do not add osc circuits, osc harnesses, or osc “keepalive” that is actually a new oscillator. The ring already exists. Electrons traverse; they do not deplete. Leave the osc line alone.

## No host eval

The host does not evaluate gates. No resident ripple, no `for g: v[o]=~(v[a]&v[b])` as runtime, no host forward pass, no recreating the model as a Python inference engine. `pfc_llama_decode` (host-eval of Llama) is the forbidden crutch. Runtime is inject + surface. Fabrication-time verification of a *new* circuit (before it is stored) is a different verb and is not this pack.

## No parallel fab

Do not fabricate in parallel with other agents into the same binary. That is how `muhl_lane_bank_002` died. One writer at a time, or no writer. This revenue pack writes **docs only**. It does not fab.

## Llama already edited

The Llama on this machine is not stock. It was already White Box-edited (sighted meaning-edit, no inference). Smol is the control that was left alone. Do not “install a fresh 70B” as if the work had not been done. Do not re-edit Llama to prove White Box again. Serve or show the edited file; do not recreate it.

## What this pack is allowed to be

Three new markdown files in this directory. Revenue documents. No binary. No circuit. No commit.
