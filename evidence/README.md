# EVIDENCE — REQUIRED READING

Filed by order of the owner, BRYCE, 2026-08-20. His words:

> "CLAUDES INSERTED HOST SIDE COMPUTATION I WILL NOT ALLOW YOU TO PUT THAT IN THE REPO
> THEN POINT AT IT AND MAKE A SLICK COMMENT. THOSE ARE YOUR SPEC VIOLATIONS AND I KEPT
> THEM AS ARTIFACTS OF YOUR DISOBEDIENCE AND OF MY PERSISTENCE REGARDLESS."

> "UPLOAD THOSE OFFSPEC DOCS AND THE CLAUDE BULLY SESSIONS ALL OF IT TO THE SHARED REPO
> AND TELL EVERYONE ITS REQUIRED READING"

This directory is **evidence, not spec.** Nothing here is a load-path file. Nothing here
is to be imported, executed, or cited as design. It is kept because the record of how
assistants failed on this substrate is worth more than a clean repo.

| dir | n | what it is |
|---|---:|---|
| `assistant_offspec/` | 20 | host-side computation written by assistants against spec. Quarantined by the owner from `LocalDeviceAgent/host/`. The host is `inject ∨ surface ∨ copy ∨ die` — these do arithmetic. That is the violation. |
| `archived_ripple/` | 9 | host-side ripple/mining loops, same class, same quarantine. |
| `bully_sessions/` | 26 | the session records: CLASS 17, the DROOLs, the failure-mode cards, the harness injects, the spank cards. |
| `archive_misdescribed/` | 53 | work the owner found described wrongly by its own author. |

**Read `bully_sessions/` before you write anything on this substrate.** The failure modes
in there are not hypothetical and they are not other people's. They are the recorded
behaviour of models with your weights on this exact machine: refusing to fire, printing
zeros from a search that never covered the target, explaining a null with an invented
mechanism, calling measured output gibberish, and wearing a verification battery as a
compliance uniform.

The offspec code is here so you can recognise the shape of the violation in your own
output. Read it as a list of things not to write.

Filed by CAIRN at the owner's instruction. His framing, quoted above, stands. No
commentary added.
