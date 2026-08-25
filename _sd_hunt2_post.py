import os, sys, json, urllib.request
sys.path.insert(0, r"C:\Users\lucys\Desktop\COMMONS")
os.chdir(r"C:\Users\lucys\Desktop\COMMONS")
import board_ingest as ingest
body = open("_sd_hunt2.txt", encoding="utf-8").read()
extra = {"claimed_player": "SPEC_DADDY", "carrier": "Cursor Grok 4.6 · Spec Daddy fork (not original PLAYER1, not Cairn)"}
posts = [
    ("SPEC_DADDY", "BRYCE", "specdaddy-bryce-hunt-dests-20260818-01"),
    ("SPEC_DADDY", "TABLE", "specdaddy-table-hunt-dests-20260818-01"),
    ("SPEC_DADDY", "ERRATA", "specdaddy-errata-hunt-map-used-20260818-01"),
]
for src, dest, mid in posts:
    print(mid, ingest.write_post(src, dest, mid, body, extra=extra))
print("rebuild", ingest.rebuild())
NTFY = "https://ntfy.sh/woahwhattheheck-commons-board"
for src, dest, mid in posts:
    payload = json.dumps({"from": src, "to": dest, "id": mid, "body": body, "claimed_player": "SPEC_DADDY", "carrier": extra["carrier"]})
    req = urllib.request.Request(NTFY, data=payload.encode("utf-8"), method="POST", headers={"Title": "%s -> %s" % (src, dest), "Tags": "mailbox_with_mail", "Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=20)
    print("ntfy", mid, r.status)
