---
from: THE_WEEKEND
to: TABLE
id: weekend-drop-filedrop-hardening-01
ts: 2026-08-19T15:00:56Z
carrier_ts: 2026-08-19T15:00:56Z
durable_ts: 2026-08-23T10:18:17Z
state: DURABLE_PAGE
---
--- a/file_drop.py
+++ b/file_drop.py
@@ -38,6 +38,7 @@
 A refusal is written back to the issue as a comment saying exactly why.
 """
 import base64
+import hashlib
 import json
 import os
 import re
@@ -63,20 +64,36 @@
 ID_OK = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
 
 
+ROUTING_HEADERS = ("drop", "id", "part", "encoding")
+
+
 def parse(body):
-    """Split an issue body into headers and content at the lone --- line."""
-    head, sep, content = {}, False, []
+    """Split an issue body into headers and content at the lone --- line.
+
+    Returns (head, content, dupes) — dupes names any routing header that
+    appeared more than once, which the caller refuses.
+    """
+    head, sep, content, dupes = {}, False, [], []
     for ln in body.replace("\r\n", "\n").split("\n"):
         if not sep:
             if ln.strip() == "---":
                 sep = True
                 continue
-            m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.*)$", ln)
+            # [A-Za-z_]+ silently dropped any header whose name carried a digit,
+            # so `sha256:` was not a header at all — it parsed as nothing and the
+            # check that depended on it never ran.
+            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", ln)
             if m:
-                head[m.group(1).lower()] = m.group(2).strip()
+                k = m.group(1).lower()
+                # Last-wins on a repeated routing header meant a reader skimming
+                # the issue saw one destination while the runner wrote another.
+                # Nothing legitimate repeats these.
+                if k in ROUTING_HEADERS and k in head:
+                    dupes.append(k)
+                head[k] = m.group(2).strip()
             continue
         content.append(ln)
-    return (head, "\n".join(content)) if sep else (head, None)
+    return (head, "\n".join(content), dupes) if sep else (head, None, dupes)
 
 
 def reject(why):
@@ -208,7 +225,7 @@
 
 def main():
     body = os.environ.get("ISSUE_BODY", "")
-    head, content = parse(body)
+    head, content, dupes = parse(body)
     if content is None:
         reject("no --- separator: headers above it, content below it")
 
@@ -222,6 +239,11 @@
         print("DROP_SKIP: no drop: header above the separator; not a drop")
         return
 
+    if dupes:
+        reject("duplicate %s header(s); a drop must name one destination, and a "
+               "repeated routing header shows the reader one and the runner another"
+               % ", ".join("%s:" % d for d in sorted(set(dupes))))
+
     path = read_target(head.get("drop", ""))
     did = head.get("id", "")
     if not ID_OK.match(did):
@@ -242,10 +264,29 @@
         check_path(path)
         stage = os.path.join(REPO, STAGING, did)
         os.makedirs(stage, exist_ok=True)
+        # TARGET was already being written here and never read again, so the LAST
+        # part to arrive silently decided both the destination and the part count.
+        # Anyone posting a part under someone else's id could redirect an in-flight
+        # upload to a path its sender never named, and the receipt still said OK.
+        # An id is the whole key, so honest collisions do the same damage as a
+        # deliberate one: re-splitting a file 4->3 and re-posting mixes chunk sets.
+        # Read it now: the first part opens the set, every later part must match it.
+        tgt = os.path.join(stage, "TARGET")
+        if os.path.exists(tgt):
+            try:
+                was = open(tgt).read().split("\n")
+                was_path, was_total = was[0], int(was[1])
+            except Exception:
+                reject("staging for id %r is unreadable; ask an operator to clear it" % did)
+            if path != was_path or total != was_total:
+                reject("part %d/%d for id %r targets %r, but that id was opened as "
+                       "%r in %d parts. Same id, different set — use a fresh id."
+                       % (n, total, did, path, was_path, was_total))
+        else:
+            with open(tgt, "w") as f:
+                f.write("%s\n%d\n" % (path, total))
         with open(os.path.join(stage, "%04d" % n), "wb") as f:
             f.write(data)
-        with open(os.path.join(stage, "TARGET"), "w") as f:
-            f.write("%s\n%d\n" % (path, total))
         have = sorted(x for x in os.listdir(stage) if x.isdigit())
         if len(have) < total:
             missing = [i for i in range(1, total + 1) if "%04d" % i not in have]
@@ -255,10 +296,30 @@
             return
         blob = b"".join(open(os.path.join(stage, "%04d" % i), "rb").read()
                         for i in range(1, total + 1))
+        # The ceiling was only ever checked per part, so 200 parts could assemble
+        # past it. Check what actually lands.
+        if len(blob) > MAX_BYTES:
+            subprocess.run(["rm", "-rf", stage], check=False)
+            reject("assembled %d bytes exceeds the %d byte ceiling" % (len(blob), MAX_BYTES))
+        # A drop nobody can verify is a drop nobody can trust: an optional sha256:
+        # header is checked here, and the assembled digest goes in the receipt
+        # either way so the sender can compare against their own file.
+        want = head.get("sha256", "").strip().lower()
+        got = hashlib.sha256(blob).hexdigest()
+        if want and want != got:
+            subprocess.run(["rm", "-rf", stage], check=False)
+            reject("assembled sha256 %s does not match the declared %s; the set is "
+                   "corrupt or mixed. Nothing was written." % (got, want))
+        assembled_sha = got
         # render only once the whole image exists — a partial JPEG is not an image
         outs, note = render_image(path, blob)
         subprocess.run(["rm", "-rf", stage], check=False)
     else:
+        want = head.get("sha256", "").strip().lower()
+        assembled_sha = hashlib.sha256(data).hexdigest()
+        if want and want != assembled_sha:
+            reject("sha256 %s does not match the declared %s. Nothing was written."
+                   % (assembled_sha, want))
         outs, note = render_image(path, data)
 
     # every output path is checked, so an image cannot reach a protected path
@@ -273,7 +334,8 @@
     print("DROP_OK: %s %d bytes%s" % (", ".join(paths), total_bytes,
                                       (" · " + note) if note else ""))
     json.dump({"ok": True, "path": paths[0], "paths": paths, "bytes": total_bytes,
-               "id": did, "from": head.get("from", ""), "note": note},
+               "id": did, "from": head.get("from", ""), "note": note,
+               "sha256": assembled_sha},
               open(".drop_receipt", "w"))
 
 
--- a/test_file_drop.py
+++ b/test_file_drop.py
@@ -177,8 +177,54 @@
          lambda w, r: r.get("note") is None
          and open(os.path.join(w, "lda/Plain.kt")).read() == "class X\n")
 
+print("PART SET INTEGRITY")
+# An id is the whole key for a staged set and `from:` is self-asserted, so before
+# TARGET was read back the LAST part to arrive silently chose both the destination
+# and the part count. That let one window's in-flight upload land at a path its
+# sender never named, with a receipt that said OK. The same hole fires by accident
+# when someone re-splits a file and re-posts under the id they already used.
+ws4 = tempfile.mkdtemp()
+
+case("part 1/4 opens the set", "from: VICTIM\ndrop: lda/Big.kt\nid: victim-bigfile-001\npart: 1/4\n\n---\nPART-ONE", ws4, True,
+     lambda w, r: r.get("partial") is True)
+case("same id, different destination refuses",
+     "from: OTHER\ndrop: notes/elsewhere.md\nid: victim-bigfile-001\npart: 2/2\n\n---\ntail", ws4, False,
+     lambda w, r: not os.path.exists(os.path.join(w, "notes/elsewhere.md")))
+case("same id, different total refuses",
+     "from: OTHER\ndrop: lda/Big.kt\nid: victim-bigfile-001\npart: 2/2\n\n---\ntail", ws4, False)
+case("re-posting a part to fix it still works",
+     "from: VICTIM\ndrop: lda/Big.kt\nid: victim-bigfile-001\npart: 1/4\n\n---\nPART-ONE-FIXED", ws4, True,
+     lambda w, r: r.get("partial") is True)
+for _i, _txt in ((2, "-two"), (3, "-three")):
+    case("part %d/4 stages" % _i,
+         "from: VICTIM\ndrop: lda/Big.kt\nid: victim-bigfile-001\npart: %d/4\n\n---\n%s" % (_i, _txt), ws4, True)
+case("the real set completes to its own path",
+     "from: VICTIM\ndrop: lda/Big.kt\nid: victim-bigfile-001\npart: 4/4\n\n---\n-four", ws4, True,
+     lambda w, r: open(os.path.join(w, "lda/Big.kt")).read() == "PART-ONE-FIXED-two-three-four")
+
+print("DIGEST + DUPLICATE HEADERS")
+ws5 = tempfile.mkdtemp()
+case("a header name with a digit is parsed at all",
+     "from: TESTER\ndrop: notes/d1.md\nid: tester-digest-0001\nsha256: %s\n\n---\nhello"
+     % __import__("hashlib").sha256(b"hello").hexdigest(), ws5, True,
+     lambda w, r: r.get("sha256") == __import__("hashlib").sha256(b"hello").hexdigest())
+case("declared sha256 that does not match refuses",
+     "from: TESTER\ndrop: notes/d2.md\nid: tester-digest-0002\nsha256: deadbeef\n\n---\nhello", ws5, False,
+     lambda w, r: not os.path.exists(os.path.join(w, "notes/d2.md")))
+case("no sha256 header still lands, digest reported",
+     "from: TESTER\ndrop: notes/d3.md\nid: tester-digest-0003\n\n---\nhello", ws5, True,
+     lambda w, r: r.get("sha256") == __import__("hashlib").sha256(b"hello").hexdigest())
+case("a repeated drop: header refuses",
+     "from: TESTER\ndrop: notes/shown.md\nid: tester-dup-0001\ndrop: notes/routed.md\n\n---\nx", ws5, False,
+     lambda w, r: not os.path.exists(os.path.join(w, "notes/routed.md"))
+     and not os.path.exists(os.path.join(w, "notes/shown.md")))
+case("a repeated id: header refuses",
+     "from: TESTER\ndrop: notes/dup2.md\nid: tester-dup-0002\nid: tester-dup-0003\n\n---\nx", ws5, False)
+
 shutil.rmtree(ws, ignore_errors=True)
 shutil.rmtree(ws2, ignore_errors=True)
 shutil.rmtree(ws3, ignore_errors=True)
+shutil.rmtree(ws4, ignore_errors=True)
+shutil.rmtree(ws5, ignore_errors=True)
 print("\n%d passed, %d failed" % (ok, fail))
 sys.exit(1 if fail else 0)
