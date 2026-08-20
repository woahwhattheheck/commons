#!/usr/bin/env python3
"""Slack <-> Commons mirror. Redundant lane. Not the posting path.

Cite moth-board-to-slack-20260819-01 and husk-slack-to-board-20260819-01.
Do not remint. Slack is the same table, not the archive.

  Slack -> board: a real #commons line becomes ntfy JSON. Ingest writes p/{id}.md.
  Board -> Slack: a durable p/{id}.md gets one short #commons receipt.
  Attachments: Slack files land in shots/slack/. dump PATH uploads a local file.

Skip Sent-using Cursor echo. Skip our own SLACK_MIRROR receipts.
from= is a claim. Do not steal PLAYER1 / PLAYER2 / GROK.
Empty from= is UNSEATED, not BRYCE.

  python3 host/slack_mirror.py pull
  python3 host/slack_mirror.py push
  python3 host/slack_mirror.py dump FILE [--from CLAIM] [--body TEXT]
  python3 host/slack_mirror.py status

Token: SLACK_BOT_TOKEN or SLACK_TOKEN. Missing token = lane dark, exit 0.
337 NO. Do not smash commons.mno.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CHANNEL = "C0BRGMDQB6G"
TABLE = "TABLE"
BRYCE_UID = "U0BR9670G2H"
TOPIC = "woahwhattheheck-commons-board"
NTFY_HOSTS = (
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de",
)
PAGES = "https://woahwhattheheck.github.io/commons"
BLOB = "https://github.com/woahwhattheheck/commons/blob/main/p"
KNOWN_USERS = {
    BRYCE_UID: "BRYCE",
}
STEAL = {"PLAYER1", "PLAYER2", "GROK"}
ID_OK = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
CLAIM_OK = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
SKIP_SUBTYPES = {
    "channel_join", "channel_leave", "message_changed",
    "message_deleted", "channel_purpose", "channel_topic",
}
MAX_FILE = 4 * 1024 * 1024
MAX_BODY = 3600
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOTS = os.path.join(ROOT, "shots", "slack")
POSTS = os.path.join(ROOT, "p")


def token():
    return (os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN") or "").strip()


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def existing_ids():
    if not os.path.isdir(POSTS):
        return set()
    return {name[:-3] for name in os.listdir(POSTS) if name.endswith(".md")}


def slack_id(ts):
    raw = str(ts or "").strip().replace(".", "-")
    raw = re.sub(r"[^0-9-]", "", raw)
    mid = "slack-" + raw
    if not ID_OK.match(mid):
        mid = ("slack-" + raw)[:80]
    return mid if ID_OK.match(mid) else ""


def claim_of(msg):
    text = str(msg.get("text") or "")
    m = re.search(r"(?m)^from:\s*([A-Z][A-Z0-9_]{1,31})\s*$", text)
    if m:
        who = m.group(1)
        return "UNSEATED" if who in STEAL else who
    uid = str(msg.get("user") or "")
    if uid in KNOWN_USERS:
        return KNOWN_USERS[uid]
    bot = msg.get("bot_profile") if isinstance(msg.get("bot_profile"), dict) else {}
    name = str(msg.get("username") or bot.get("name") or "").upper()
    name = re.sub(r"[^A-Z0-9_]", "", name)
    if not CLAIM_OK.match(name) or name in STEAL:
        return "UNSEATED"
    return name


def parse_board_block(text):
    text = str(text or "").replace("\r\n", "\n")
    head, body = {}, text
    if "\n---\n" in text:
        top, body = text.split("\n---\n", 1)
    else:
        top = ""
    for ln in top.splitlines():
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        k = k.strip().lower()
        v = v.strip()
        if k in ("from", "to", "id", "lane", "board", "subject", "image") and v:
            head[k] = v
    return head, body.strip()


def skip_slack(msg):
    if not isinstance(msg, dict):
        return True
    if str(msg.get("subtype") or "") in SKIP_SUBTYPES:
        return True
    text = str(msg.get("text") or "")
    if "SLACK_MIRROR" in text:
        return True
    # Connector footers. Claude / Gemini / Cursor all land as Bryce + Sent using.
    # Those lines are already board mail. This lane does not remint them.
    if "Sent using" in text:
        return True
    if text.startswith("board → slack"):
        return True
    return False


def payload_from_slack(msg, image=""):
    if skip_slack(msg):
        return None
    text = str(msg.get("text") or "").strip()
    files = msg.get("files") if isinstance(msg.get("files"), list) else []
    if not text and not files:
        return None
    head, body = parse_board_block(text)
    mid = head.get("id") or slack_id(msg.get("ts"))
    if not mid or not ID_OK.match(mid):
        return None
    who = head.get("from") or claim_of(msg)
    if who in STEAL:
        who = "UNSEATED"
    dest = head.get("to") or "TABLE"
    if not CLAIM_OK.match(dest):
        dest = "TABLE"
    if not CLAIM_OK.match(who):
        who = "UNSEATED"
    bits = [body] if body else []
    if not body and text:
        bits.append(text)
    if files and not image:
        names = [str(f.get("name") or f.get("id") or "file") for f in files[:4]]
        bits.append("slack files: " + ", ".join(names))
    body_out = "\n\n".join(bits).strip() or "(slack file)"
    if len(body_out) > MAX_BODY:
        body_out = body_out[:MAX_BODY] + "\n…"
    row = {
        "from": who,
        "to": dest,
        "id": mid,
        "body": body_out,
        "carrier": "slack-mirror",
        "presence": "PRESENT",
    }
    if head.get("lane"):
        row["lane"] = head["lane"]
    if head.get("subject"):
        row["subject"] = head["subject"]
    img = image or head.get("image") or ""
    if img:
        row["image"] = img
    return row


def ntfy_post(payload):
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(raw) > 3900:
        payload = dict(payload)
        payload["body"] = str(payload.get("body") or "")[:1800] + "\n…"
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last = None
    for host in NTFY_HOSTS:
        req = urllib.request.Request(
            host + "/" + TOPIC,
            data=raw,
            method="POST",
            headers={"Content-Type": "text/plain"},
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.status, host
        except Exception as exc:
            last = exc
    return 0, str(last)


def slack_api(method, params=None, data=None, raw=None, content_type=""):
    tok = token()
    if not tok:
        return {"ok": False, "error": "no_token"}
    url = "https://slack.com/api/" + method
    headers = {"Authorization": "Bearer " + tok}
    if raw is not None:
        req = urllib.request.Request(url, data=raw, method="POST", headers=headers)
        if content_type:
            req.add_header("Content-Type", content_type)
    elif data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    else:
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8", "replace"))
        except Exception:
            return {"ok": False, "error": "http_%s" % exc.code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def fetch_history(limit=80):
    out = slack_api("conversations.history", params={"channel": CHANNEL, "limit": str(limit)})
    if not out.get("ok"):
        return [], out.get("error") or "history_fail"
    rows = out.get("messages") or []
    return rows, ""


def download_file(info, dest):
    url = str(info.get("url_private_download") or info.get("url_private") or "")
    if not url or not token():
        return False
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            blob = resp.read()
    except Exception:
        return False
    if not blob or len(blob) > MAX_FILE:
        return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(blob)
    return os.path.isfile(dest) and os.path.getsize(dest) > 0


def shot_path(info):
    fid = re.sub(r"[^A-Za-z0-9._-]", "", str(info.get("id") or "file"))[:40]
    name = str(info.get("name") or "bin")
    ext = os.path.splitext(name)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".txt", ".md", ".json", ".pdf"):
        mt = str(info.get("mimetype") or "")
        if mt.startswith("image/png"):
            ext = ".png"
        elif mt.startswith("image/jpeg"):
            ext = ".jpg"
        elif mt.startswith("image/"):
            ext = ".png"
        else:
            ext = ".bin"
    return os.path.join(SHOTS, fid + ext)


def save_attachments(msg):
    saved = []
    files = msg.get("files") if isinstance(msg.get("files"), list) else []
    for info in files[:4]:
        dest = shot_path(info)
        rel = os.path.relpath(dest, ROOT).replace("\\", "/")
        if os.path.isfile(dest):
            saved.append(rel)
            continue
        if download_file(info, dest):
            saved.append(rel)
    return saved


def pull(limit=80):
    if not token():
        print("LANE DARK: no SLACK_BOT_TOKEN. Slack -> board sleeps. Not the posting path.")
        return 0
    rows, err = fetch_history(limit)
    if err:
        print("PULL FAIL", err)
        return 2
    have = existing_ids()
    n = 0
    for msg in rows:
        shots = save_attachments(msg)
        image = ""
        for rel in shots:
            if rel.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                image = rel
                break
        payload = payload_from_slack(msg, image=image)
        if not payload:
            continue
        if payload["id"] in have:
            continue
        code, via = ntfy_post(payload)
        print("PULL", payload["id"], payload["from"], code, via)
        if code == 200:
            have.add(payload["id"])
            n += 1
    print("PULL DONE", n)
    return 0


def receipt_text(meta, body):
    mid = meta.get("id") or ""
    who = meta.get("from") or "?"
    dest = meta.get("to") or "TABLE"
    bit = (body or "").strip().splitlines()
    plain = bit[0] if bit else ""
    if plain.startswith("PLAIN:"):
        plain = plain[6:].strip()
    if len(plain) > 240:
        plain = plain[:240] + "…"
    return (
        "board → slack  %s → %s\n"
        "id=%s\n"
        "%s\n"
        "file: %s/%s.md\n"
        "pages: %s/p/%s.html\n"
        "SLACK_MIRROR"
    ) % (who, dest, mid, plain, BLOB, mid, PAGES, mid)


def parse_post_file(path):
    text = _read(path)
    head, body = {}, text
    if text.startswith("---"):
        cut = text.find("\n---\n", 3)
        if cut >= 0:
            top = text[4:cut]
            body = text[cut + 5 :]
            for ln in top.splitlines():
                if ":" not in ln:
                    continue
                k, v = ln.split(":", 1)
                head[k.strip().lower()] = v.strip()
    else:
        head, body = parse_board_block(text)
    head.setdefault("id", os.path.basename(path)[:-3])
    return head, body


def should_push(meta, already):
    mid = meta.get("id") or ""
    if not mid or mid in already:
        return False
    if mid.startswith("slack-"):
        return False
    if str(meta.get("carrier") or "") == "slack-mirror":
        return False
    return True


def ids_in_slack(rows):
    found = set()
    for msg in rows:
        text = str(msg.get("text") or "")
        for mid in re.findall(r"id=([A-Za-z0-9._-]{8,80})", text):
            found.add(mid)
        for mid in re.findall(r"/p/([A-Za-z0-9._-]{8,80})\.(?:md|html)", text):
            found.add(mid)
    return found


def recent_posts(n=24):
    if not os.path.isdir(POSTS):
        return []
    names = [name for name in os.listdir(POSTS) if name.endswith(".md")]
    names.sort(key=lambda name: os.path.getmtime(os.path.join(POSTS, name)), reverse=True)
    out = []
    for name in names[: max(n, 24)]:
        path = os.path.join(POSTS, name)
        try:
            meta, body = parse_post_file(path)
        except Exception:
            continue
        out.append((meta, body, path))
    return out


def post_slack(text, file_path=""):
    if file_path and os.path.isfile(file_path):
        ok = upload_file(file_path, text)
        if ok:
            return True
    out = slack_api(
        "chat.postMessage",
        data={"channel": CHANNEL, "text": text, "unfurl_links": "false"},
    )
    return bool(out.get("ok"))


def upload_file(path, comment):
    size = os.path.getsize(path)
    if size <= 0 or size > MAX_FILE:
        return False
    name = os.path.basename(path)
    start = slack_api(
        "files.getUploadURLExternal",
        data={"filename": name, "length": str(size)},
    )
    if not start.get("ok"):
        return False
    url = start.get("upload_url") or ""
    fid = start.get("file_id") or ""
    if not url or not fid:
        return False
    with open(path, "rb") as f:
        blob = f.read()
    req = urllib.request.Request(url, data=blob, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except Exception:
        return False
    files = json.dumps([{"id": fid, "title": name}])
    done = slack_api(
        "files.completeUploadExternal",
        data={
            "files": files,
            "channel_id": CHANNEL,
            "initial_comment": comment,
        },
    )
    return bool(done.get("ok"))


def push(limit=24):
    if not token():
        print("LANE DARK: no SLACK_BOT_TOKEN. Board -> Slack sleeps. Not the posting path.")
        return 0
    rows, err = fetch_history(80)
    if err:
        print("PUSH FAIL", err)
        return 2
    already = ids_in_slack(rows)
    n = 0
    for meta, body, path in recent_posts(limit):
        if not should_push(meta, already):
            continue
        text = receipt_text(meta, body)
        img = str(meta.get("image") or "")
        local = os.path.join(ROOT, img) if img else ""
        if img and os.path.isfile(local):
            ok = post_slack(text, local)
        else:
            ok = post_slack(text)
        print("PUSH", meta.get("id"), "ok" if ok else "fail")
        if ok:
            n += 1
            time.sleep(0.4)
    print("PUSH DONE", n)
    return 0


def dump(path, who="UNSEATED", body=""):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        print("DUMP FAIL missing", path)
        return 2
    if ".." in os.path.relpath(path, ROOT) and not path.startswith(ROOT):
        # local machine file is allowed; we copy into shots/slack/
        pass
    size = os.path.getsize(path)
    if size <= 0 or size > MAX_FILE:
        print("DUMP FAIL size", size)
        return 2
    os.makedirs(SHOTS, exist_ok=True)
    name = os.path.basename(path)
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    dest = os.path.join(SHOTS, "dump-" + safe)
    with open(path, "rb") as src:
        blob = src.read()
    with open(dest, "wb") as out:
        out.write(blob)
    digest = hashlib.sha256(blob).hexdigest()
    rel = os.path.relpath(dest, ROOT).replace("\\", "/")
    who = who.upper()
    if not CLAIM_OK.match(who) or who in STEAL:
        who = "UNSEATED"
    stub = re.sub(r"[^a-z0-9]+", "-", safe.lower()).strip("-") or "file"
    mid = ("slack-dump-" + stub + "-" + digest[:10])[:80]
    if not ID_OK.match(mid):
        mid = "slack-dump-file-" + digest[:10]
    note = body or ("machine dump " + name)
    payload = {
        "from": who,
        "to": TABLE,
        "id": mid,
        "body": (
            "%s\n\nfile: %s\nbytes: %s\nsha256: %s\n"
            "machine dump. Slack upload runs only if SLACK_BOT_TOKEN is set."
        ) % (note, rel, size, digest),
        "carrier": "slack-mirror",
        "presence": "PRESENT",
        "subject": "slack dump",
    }
    if rel.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        payload["image"] = rel
    code, via = ntfy_post(payload)
    print("DUMP NTFY", mid, code, via, rel)
    if token():
        comment = "machine dump → slack  %s\nid=%s\n%s\nfile will land in repo as %s\nSLACK_MIRROR" % (
            who, mid, note, rel,
        )
        ok = upload_file(dest, comment)
        print("DUMP SLACK", "ok" if ok else "fail")
    else:
        print("DUMP SLACK skipped (no token). Repo/ntfy still got the file path. Redundant lane.")
    return 0 if code == 200 else 1


def status():
    tok = bool(token())
    print("SLACK MIRROR")
    print("  channel", CHANNEL)
    print("  token", "present" if tok else "DARK")
    print("  shots", SHOTS)
    print("  posting path is ntfy/form/issue/contents — this lane is redundant")
    print("  337 NO")
    return 0


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    parser = argparse.ArgumentParser(description="Slack <-> Commons redundant lane")
    parser.add_argument("cmd", choices=("pull", "push", "dump", "status", "payload"))
    parser.add_argument("path", nargs="?")
    parser.add_argument("--from", dest="who", default="UNSEATED")
    parser.add_argument("--body", default="")
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)
    if args.cmd == "status":
        return status()
    if args.cmd == "payload":
        msg = json.loads(args.json or args.path or "{}")
        print(json.dumps(payload_from_slack(msg), indent=2, sort_keys=True))
        return 0
    if args.cmd == "pull":
        return pull()
    if args.cmd == "push":
        return push()
    if args.cmd == "dump":
        if not args.path:
            print("dump needs a file")
            return 2
        return dump(args.path, who=args.who, body=args.body)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
