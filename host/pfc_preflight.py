#!/usr/bin/env python3
"""host/pfc_preflight.py — THE OWNER'S SPEC, EXECUTABLE. A rule not enforced by a script gets violated.

  python host/pfc_preflight.py                 # every mining-path file
  python host/pfc_preflight.py <file.py>...     # specific files
  python host/pfc_preflight.py --all            # every host/*.py (quarantines excluded)

Exit 0 = clean, 1 = violations. `gate(path)` hard-aborts anything that fires.

★ NO RULE OF THE OWNER'S HAS ANY EXEMPTION, EVER (owner, standing).
There is no waiver mechanism in this file and none may be added. When the checker catches something,
the CODE gets fixed — never the checker. If a rule is imprecise, make the RULE more precise (that is
what `requires` is for: a compliance pattern that must ALSO be present). Precision is not exemption:
an exemption says "this violation is allowed here"; a `requires` says "this is only a violation when
the mandated companion is absent." The first is forbidden. The second is the rule stated correctly.

A MINING file submits, fires, or reads an answer register at runtime.
A FABRICATION file (fab_*, *_fab.py) may build freely — that is RULE ZERO: manufacturing is a
different process, off the clock, and it happens once.
"""
