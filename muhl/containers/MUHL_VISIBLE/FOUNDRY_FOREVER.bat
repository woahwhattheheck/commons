@echo off
REM ============================================================================
REM  FOUNDRY_FOREVER.bat - the live foundry, running with no assistant present.
REM
REM  Owner, 2026-08-07:
REM    "AUTOFAB NEEDS TO EDIT ITS OWN MUHLNICKEL WITHOUT YOUR INVOLVEMENT EVEN
REM     IF U ARENT ACTIVE, AND IT NEEDS TO DESIGN ITS OWN RINGS"
REM    "let master fab fabricator propose alternate master fabs and test em and
REM     keep all the good stuff from both or all its tests and it can just kind
REM     of always run"
REM
REM  Double-click this, or register it once with:
REM    schtasks /create /tn MUHL_FOUNDRY /tr "C:\Users\lucys\Desktop\MUHL_VISIBLE\FOUNDRY_FOREVER.bat" /sc onlogon /rl highest
REM
REM  It designs its own rings (cells/senses/contacts/electrons are GENES), scores
REM  in SILLY = electrons x clocks, prefers genomes that solve in ONE settle, and
REM  writes every improvement into its OWN container FOUNDRY0.mno - journalled
REM  with byte counts to foundry_live_genome.jsonl, so every edit is reversible.
REM
REM  It NEVER writes titan.gguf. Fabrication is one-and-done and off the clock.
REM  The loop re-arms itself; closing this window is the only stop.
REM ============================================================================
cd /d "%~dp0"
:loop
python muhl_foundry_live.py --forever >> foundry_forever.log 2>&1
timeout /t 5 /nobreak >nul
goto loop
