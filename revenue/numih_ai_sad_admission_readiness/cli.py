from __future__ import annotations
import argparse, json, os, stat
from pathlib import Path
from .compiler import compile_packet, loads_strict, render_markdown

def _read(path: Path) -> str:
    if path.is_symlink():
        raise SystemExit(f"refusing symlink input: {path}")
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > 2_000_000:
        raise SystemExit("input must be a regular file <= 2MB")
    return path.read_text(encoding="utf-8")

def _write_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--json-out", type=Path)
    p.add_argument("--markdown-out", type=Path)
    a = p.parse_args(argv)
    result = compile_packet(loads_strict(_read(a.input)))
    js = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if a.json_out: _write_new(a.json_out, js)
    else: print(js, end="")
    if a.markdown_out: _write_new(a.markdown_out, render_markdown(result) + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
