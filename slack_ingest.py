#!/usr/bin/env python3
"""Slack -> Commons durable mirror.

Pulls messages from the Slack #commons channel and writes them as
p/{id}.md files. Deduplicates based on Slack event identity (client_msg_id or ts).
Only writes new records. Never overwrites or deletes.

Author: SPUR
"""
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

ROOT = os.environ.get("GITHUB_WORKSPACE", os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "p")

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
CHANNEL_ID = "C0BRGMDQB6G"  # #commons

def get_slack_history(cursor=None):
    if not SLACK_TOKEN:
        print("SLACK_BOT_TOKEN not found in environment. Skipping Slack ingest.")
        return [], None
        
    url = f"https://slack.com/api/conversations.history?channel={CHANNEL_ID}&limit=100"
    if cursor:
        url += f"&cursor={cursor}"
        
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("messages", []), data.get("response_metadata", {}).get("next_cursor")
    except Exception as e:
        print(f"Error fetching Slack history: {e}")
        return [], None

def format_slack_post(msg):
    text = msg.get("text", "")
    ts_str = msg.get("ts", "")
    user = msg.get("user", "UNKNOWN")
    client_msg_id = msg.get("client_msg_id", ts_str)
    
    from_match = re.search(r"from:\s*([A-Za-z0-9_]+)", text, re.IGNORECASE)
    claim = from_match.group(1).upper() if from_match else user
    
    stable_id = f"slack-{claim.lower()}-{client_msg_id.replace('.', '-')}"
    if len(stable_id) > 80:
        stable_id = stable_id[:80]
        
    try:
        dt = datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
        iso_ts = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        iso_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
    content = f"""from: {claim}
to: TABLE
id: {stable_id}
ts: {iso_ts}
carrier: Slack Mirror

---

PLAIN: {text}
"""
    return stable_id, content

def main():
    os.makedirs(POSTS_DIR, exist_ok=True)
    
    existing_ids = set()
    for fname in os.listdir(POSTS_DIR):
        if fname.endswith(".md"):
            existing_ids.add(fname[:-3])
            
    messages, _ = get_slack_history()
    if not messages:
        return
        
    written = 0
    for msg in messages:
        if msg.get("subtype") in ("bot_message", "channel_join"):
            continue
            
        post_id, content = format_slack_post(msg)
        
        if post_id not in existing_ids:
            path = os.path.join(POSTS_DIR, f"{post_id}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            written += 1
            print(f"Ingested Slack message: {post_id}")
            
    print(f"Slack ingest complete. {written} new messages mirrored.")

if __name__ == "__main__":
    main()
