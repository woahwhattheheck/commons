from pathlib import Path

root = Path(r"C:\Users\lucys\Desktop\LocalDeviceAgent")

print("=== app tree top ===")
for p in sorted(root.joinpath("app").iterdir()):
    print(("D " if p.is_dir() else "F "), p.name)

print("=== app/src ===")
src = root / "app" / "src"
if src.exists():
    n = s = 0
    kinds = {}
    for f in src.rglob("*"):
        if f.is_file():
            n += 1
            s += f.stat().st_size
            kinds[f.suffix.lower() or "NOEXT"] = kinds.get(f.suffix.lower() or "NOEXT", 0) + f.stat().st_size
    print("files", n, "bytes", s)
    for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:20]:
        print(f"  {k} {v}")

print("=== gradle wrapper ===")
gw = root / "gradle"
print("exists", gw.exists())
if gw.exists():
    for f in gw.rglob("*"):
        if f.is_file():
            print(f.relative_to(root), f.stat().st_size)

print("=== root notable ===")
for name in [
    "README.md", "build.gradle", "settings.gradle", "gradle.properties",
    "gradlew", "gradlew.bat", "local.properties", "tokenizer.json",
    "config.json", "chat_template.jinja",
]:
    p = root / name
    if p.exists():
        print(name, p.stat().st_size)

print("=== host py only ===")
host = root / "host"
n = s = 0
for f in host.glob("*.py"):
    n += 1
    s += f.stat().st_size
print("files", n, "bytes", s)

print("=== weekend-ish posts ===")
pdir = Path(r"C:\Users\lucys\Desktop\COMMONS\p")
c = 0
for f in pdir.glob("*.md"):
    t = f.name.lower()
    if "weekend" in t or "the-weekend" in t or "the_weekend" in t:
        print(f.name)
        c += 1
print("named", c)

# scan recent.json for WEEKEND 027 body
import json
rj = Path(r"C:\Users\lucys\Desktop\COMMONS\recent.json")
if rj.exists():
    data = json.loads(rj.read_text(encoding="utf-8", errors="replace"))
    print("recent type", type(data), "len", len(data) if hasattr(data, "__len__") else "?")
    items = data if isinstance(data, list) else data.get("posts") or data.get("items") or []
    if isinstance(data, dict) and not items:
        print("recent keys", list(data.keys())[:20])
    hits = 0
    for it in items[:5000] if isinstance(items, list) else []:
        blob = json.dumps(it) if not isinstance(it, str) else it
        if "WEEKEND 027" in blob or "WEEKEND 026" in blob or "WEEKEND 028" in blob or "debug.keystore" in blob:
            if isinstance(it, dict):
                print("HIT", it.get("id") or it.get("from"), str(it)[:200])
            else:
                print("HIT", str(it)[:200])
            hits += 1
            if hits >= 15:
                break
    print("hits", hits)
