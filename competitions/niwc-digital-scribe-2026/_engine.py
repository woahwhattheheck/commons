#!/usr/bin/env python3
from pathlib import Path
_here = Path(__file__).resolve().parent
_src = "".join((_here / name).read_text(encoding="utf-8") for name in ("_engine_part0.py", "_engine_part1.py", "_engine_part2.py"))
exec(compile(_src, str(_here / "_engine.py"), "exec"), globals())
