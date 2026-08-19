# SIZE_ONLY — upload gate

BRYCE-1787147064303-jctjjq: the only upload constraint is **size**. Do not invent a wont-ship list of source files.

Still named (not "security theater on Kotlin"):
- `app/debug.keystore` — signing material (Weekend 026)
- `*.gguf` `*.mno` `*.litertlm` `titan.gguf` — weights / live computers, size+binary

Kotlin, docs, datasheets, LANG, dest maps FROM FILE: dump them.

If a file is too big for one GitHub issue (65536 chars), use `part: n/m` on DROP.md. If too big for git, split or compress. Size is the gate. Not "I will not paste."
