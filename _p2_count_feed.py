import re
import subprocess

t = subprocess.check_output(
    ["git", "show", "origin/main:index.html"],
    encoding="utf-8",
    errors="replace",
)
arts = re.findall(r'data-from="([^"]+)"[^>]*data-id="([^"]+)"', t)
print("n", len(arts))
for a in arts:
    print(a[0], a[1])
print("FEED_END", "<!--/RECENT_FEED-->" in t)
print("OWNER_PIN", "OWNER_PIN" in t)
m = re.search(r'data-limit="(\d+)"', t)
print("data-limit", m.group(1) if m else None)

