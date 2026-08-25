"""Copy LDA source + WhiteBox dumps into COMMONS/lda and COMMONS/whitebox_dump.
Owner order 2026-08-19: upload files needed. Exclude debug.keystore, weights, .mno, titan.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

SRC = Path(r"C:\Users\lucys\Desktop\LocalDeviceAgent")
COMMONS = Path(r"C:\Users\lucys\Desktop\COMMONS")
LDA = COMMONS / "lda"
WB_OUT = COMMONS / "whitebox_dump"
WB_SRC = Path(r"C:\Users\lucys\Desktop\WhiteBox_Research_Archive")

SKIP_NAMES = {
    "debug.keystore",
    "local.properties",
    "titan.gguf",
    ".DS_Store",
}
SKIP_SUFFIX = {".gguf", ".mno", ".crdownload", ".apk", ".aab", ".pyc"}
SKIP_DIR_NAMES = {
    ".git",
    ".gradle",
    "build",
    "__pycache__",
    "worktrees",
    "devoured",
    "titan",
    ".kotlin",
}


def skip_file(p: Path) -> bool:
    name = p.name.lower()
    if name in {n.lower() for n in SKIP_NAMES}:
        return True
    if p.suffix.lower() in SKIP_SUFFIX:
        return True
    if name.endswith(".keystore"):
        return True
    return False


def copy_tree(src: Path, dst: Path) -> tuple[int, int]:
    n = b = 0
    if src.is_file():
        if skip_file(src):
            return 0, 0
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return 1, dst.stat().st_size
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        rel_parts = f.relative_to(src).parts
        if any(part in SKIP_DIR_NAMES or part.lower() in SKIP_DIR_NAMES for part in rel_parts):
            continue
        if skip_file(f):
            continue
        dest = dst / f.relative_to(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        n += 1
        b += dest.stat().st_size
    return n, b


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if LDA.exists():
        shutil.rmtree(LDA)
    LDA.mkdir(parents=True)

    copied: list[tuple[str, int, int]] = []

    # Android + gradle project
    for rel in [
        "app/src",
        "app/build.gradle",
        "app/proguard-rules.pro",
        "build.gradle",
        "settings.gradle",
        "gradle.properties",
        ".gitignore",
        ".gitattributes",
        "README.md",
        "AUTHORSHIP.md",
        "START_HERE.md",
        "CLAUDE.md",
        "sku",
        "tools",
        ".github",
    ]:
        src = SRC / rel
        if not src.exists():
            print("MISSING", rel)
            continue
        n, b = copy_tree(src, LDA / rel)
        copied.append((rel, n, b))
        print(f"copied {rel}: files={n} bytes={b}")

    # host routing buttons / instruments (python only)
    host_src = SRC / "host"
    host_dst = LDA / "host"
    hn = hb = 0
    for f in host_src.glob("*.py"):
        if skip_file(f):
            continue
        dest = host_dst / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        hn += 1
        hb += dest.stat().st_size
    for f in host_src.glob("*.md"):
        dest = host_dst / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        hn += 1
        hb += dest.stat().st_size
    copied.append(("host/*.py+md", hn, hb))
    print(f"copied host py+md: files={hn} bytes={hb}")

    # docs minus giant logs
    docs_src = SRC / "docs"
    docs_dst = LDA / "docs"
    dn = db = 0
    if docs_src.exists():
        for f in docs_src.rglob("*"):
            if not f.is_file():
                continue
            rel_parts = f.relative_to(docs_src).parts
            if any(part.lower() in {"logs"} for part in rel_parts):
                continue
            if skip_file(f):
                continue
            if f.suffix.lower() in {".tsv", ".bin"}:
                continue
            if f.stat().st_size > 8_000_000:
                print("skip huge doc", f.relative_to(docs_src), f.stat().st_size)
                continue
            dest = docs_dst / f.relative_to(docs_src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            dn += 1
            db += dest.stat().st_size
    copied.append(("docs", dn, db))
    print(f"copied docs: files={dn} bytes={db}")

    # WhiteBox dumps (no GGUF)
    if WB_OUT.exists():
        shutil.rmtree(WB_OUT)
    WB_OUT.mkdir(parents=True)
    wb_files = [
        WB_SRC / "_INDEX.json",
        WB_SRC / "WHITEBOX_ALL_MODELS.md",
        WB_SRC / "WHITEBOX_ALL_MODELS.json",
        Path(r"C:\Users\lucys\Desktop\WHITEBOX_DATA_DUMP.md"),
        Path(r"C:\Users\lucys\Desktop\WHITEBOX_DISTRO\README.md"),
    ]
    wn = wb = 0
    for f in wb_files:
        if not f.exists():
            print("MISSING WB", f)
            continue
        dest = WB_OUT / f.name
        shutil.copy2(f, dest)
        wn += 1
        wb += dest.stat().st_size
        print(f"copied WB {f.name}: bytes={dest.stat().st_size} sha256={sha256_file(dest)}")
    copied.append(("whitebox_dump", wn, wb))

    # manifests
    lines = [
        "LDA + WhiteBox file drop 2026-08-19",
        "from SPEC_DADDY (Cursor Grok 4.6 Spec Daddy fork). Owner: upload files needed.",
        "Excluded: app/debug.keystore, *.gguf, *.mno, titan, local.properties, app/build, docs/logs tsv.",
        "",
        "COPIED:",
    ]
    total_n = total_b = 0
    for rel, n, b in copied:
        lines.append(f"  {rel}: files={n} bytes={b}")
        total_n += n
        total_b += b
    lines.append(f"TOTAL files={total_n} bytes={total_b}")
    lines.append("")
    lines.append("kotlin files under lda/app/src:")
    kt = list((LDA / "app" / "src").rglob("*.kt")) if (LDA / "app" / "src").exists() else []
    lines.append(f"  {len(kt)} .kt files")
    (LDA / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (WB_OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("DONE", "files", total_n, "bytes", total_b)


if __name__ == "__main__":
    main()
