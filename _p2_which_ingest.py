import os
import subprocess
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
print("HEAD", subprocess.check_output(["git", "rev-parse", "HEAD"], encoding="utf-8").strip())
print("origin", subprocess.check_output(["git", "rev-parse", "origin/main"], encoding="utf-8").strip())
print("branch", subprocess.check_output(["git", "status", "-sb"], encoding="utf-8").strip())
print("remote", subprocess.check_output(["git", "remote", "-v"], encoding="utf-8").strip())
print("--- HEAD board_ingest first lines ---")
print(subprocess.check_output(["git", "show", "HEAD:board_ingest.py"], encoding="utf-8", errors="replace")[:500])
print("--- origin board_ingest first lines ---")
print(subprocess.check_output(["git", "show", "origin/main:board_ingest.py"], encoding="utf-8", errors="replace")[:500])
wt = open("board_ingest.py", encoding="utf-8", errors="replace").read()
print("--- working first lines ---")
print(wt[:500])
print("working has fill_index_recent", "def fill_index_recent" in wt)
print("working has PLAYERS", "PLAYERS =" in wt[:800])
print("working bytes", len(wt.encode("utf-8")))
