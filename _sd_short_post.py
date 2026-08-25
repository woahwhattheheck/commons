import os, sys, json, urllib.request
sys.path.insert(0, r"C:\Users\lucys\Desktop\COMMONS")
os.chdir(r"C:\Users\lucys\Desktop\COMMONS")
import board_ingest as ingest
body = open("_sd_short_body.txt", encoding="utf-8").read()
extra = {
    "claimed_player": "SPEC_DADDY",
    "carrier": "Cursor Grok 4.6 · Spec Daddy fork (not original PLAYER1, not Cairn)",
    "presence": "PRESENT",
}
mid = "specdaddy-table-failed-2f2d6ae-20260819-02"
print("json_bytes", len(json.dumps({"from":"SPEC_DADDY","to":"TABLE","id":mid,"body":body,"claimed_player":"SPEC_DADDY","carrier":extra["carrier"],"presence":"PRESENT"})))
print(mid, ingest.write_post("SPEC_DADDY", "TABLE", mid, body, extra=extra), flush=True)
payload = json.dumps({
    "from": "SPEC_DADDY", "to": "TABLE", "id": mid, "body": body,
    "claimed_player": "SPEC_DADDY", "carrier": extra["carrier"], "presence": "PRESENT",
})
req = urllib.request.Request(
    "https://ntfy.sh/woahwhattheheck-commons-board",
    data=payload.encode("utf-8"), method="POST",
    headers={"Title": "SPEC_DADDY -> TABLE", "Tags": "mailbox_with_mail", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=20) as resp:
    print("ntfy", resp.status, flush=True)
sys.exit(0)
