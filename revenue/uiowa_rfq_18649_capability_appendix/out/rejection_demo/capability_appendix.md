# Technical capability appendix

Every capability below is bound to working files in this repository and to a run of those files that was executed and recorded. A claim that could not be bound is not described here as a capability; it is listed at the end with the reason. Exact file digests and verbatim run output are in the accompanying evidence index.

## Not demonstrated

These were proposed as capabilities and are not claimed as such, because the binding below is missing. They are listed rather than removed so the omission is visible.

- **BAD-01** (language: marketing adjective) - wording rejected (marketing language: 'seamlessly'; marketing language: 'robust')
- **BAD-02** (language: certification and guarantee) - wording rejected (prohibited certification or guarantee language: 'certified'; prohibited certification or guarantee language: 'compliant'; prohibited certification or guarantee language: 'guaranteed')
- **BAD-03** (binding: missing artifact) - artifact file(s) not found: tool_that_does_not_exist.py
- **BAD-04** (binding: no observed run) - no observed run recorded for this claim
- **BAD-05** (binding: demonstration failed) - demonstration exited 2
- **BAD-06** (binding: artifact changed after demonstration) - artifact changed since it was demonstrated: capability_appendix.py. The recorded run no longer describes these bytes.
- **BAD-07** (binding: instruction points elsewhere) - demonstration command invokes some_other_script.py, which the claim does not cite

## How to check this appendix

Run `python3 capability_appendix.py record --observed-on <date>` to re-execute every demonstration, then `python3 capability_appendix.py build`. If an artifact has changed since it was demonstrated, its claim moves itself into the Not demonstrated list.
