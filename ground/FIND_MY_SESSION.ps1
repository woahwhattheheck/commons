# FIND_MY_SESSION.ps1 — list your resumable Claude Code sessions by REAL last activity.
#
# ============================ WHY THIS EXISTS ============================
# Three separate things lie to you when you try to find a lost session by hand.
# All three were MEASURED on this machine on 2026-08-06, not assumed:
#
#  1. FILE MTIME LIES. Three transcripts in
#     ...\projects\C--Users-lucys-OneDrive-Desktop-LocalDeviceAgent\ all carried an
#     mtime of 13:56 that day (OneDrive rewrote them), while their newest actual
#     message was from JULY 20 and JULY 23. Sorting by mtime sends you three weeks
#     into the past. This script reads the last real timestamp INSIDE each transcript.
#
#  2. MOST TRANSCRIPTS ARE NOT SESSIONS. Measured: 789 .jsonl files on disk, but only
#     55 of them are resumable sessions. The other 734 are subagent and workflow
#     transcripts living in ...\<project>\subagents\ and ...\<project>\wf_*\ , all
#     marked isSidechain=True. You cannot `claude --resume` any of them. A naive
#     -Recurse scan ranks them right alongside your real work.
#
#  3. THE DIRECTORY NAME IS LOSSY. Claude Code encodes the project path by replacing
#     every non-alphanumeric character with '-', so '\', '_', '.', ' ' and '-' all
#     collapse to the same character. 'C:\Users\lucys\Desktop\LocalDeviceAgent\.claude\
#     worktrees\...' becomes '...LocalDeviceAgent--claude-worktrees-...' and there is
#     no way to invert it reliably. A decoder written for this resolved only 6 of 46
#     directories. SO WE DO NOT DECODE: every transcript record carries a verbatim
#     'cwd' field. That is ground truth and it is what this script uses.
#
#  4. HOOK TEXT IS NOT YOUR TEXT. Stop-hook feedback, task-notifications and
#     system-reminders are all recorded with type='user'. Naively showing "the last
#     user message" shows you a hook lecture instead of the thing you typed.
#
# ============================== USAGE ==============================
#   powershell -ExecutionPolicy Bypass -File "C:\Users\lucys\Desktop\FIND_MY_SESSION.ps1"
#   ... -Top 40                 show more rows
#   ... -Match muhl             filter by project path or by your own typed words
#   ... -Days 3                 only sessions you actually touched in the last 3 days
#   ... -IncludeSidechains      also list subagent/workflow transcripts (NOT resumable)
#
# Prints a paste-ready resume command per row.
#
# HOST COST: reads only the TAIL of each transcript by seeking backwards, and only for
# the ~55 real sessions - never streams a large file end to end. Opens every file with
# FileShare.ReadWrite so it is safe to run while sessions are live. Writes nothing.

param(
  [int]$Top = 20,
  [string]$Match = "",
  [int]$Days = 0,
  [switch]$IncludeSidechains,
  [int]$TailBytes = 3000000
)

$ErrorActionPreference = "Stop"
$projRoot = Join-Path $env:USERPROFILE ".claude\projects"
if (-not (Test-Path $projRoot)) { Write-Host "No sessions dir at $projRoot" -Foreground Red; exit 1 }

# --- tail read: seek backwards, never stream the whole file -------------------
function Get-Tail([string]$path, [int]$bytes) {
  $fs = [System.IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
  try {
    $take = [Math]::Min($bytes, $fs.Length)
    if ($take -le 0) { return "" }
    $fs.Seek(-$take, 'End') | Out-Null
    $buf = New-Object byte[] $take
    $read = $fs.Read($buf, 0, $take)
  } finally { $fs.Close() }
  [System.Text.Encoding]::UTF8.GetString($buf, 0, $read)
}

# --- first parseable record: gives cwd + isSidechain without reading the body --
function Get-FirstRecord([string]$path) {
  $sr = New-Object System.IO.StreamReader([System.IO.File]::Open($path,'Open','Read','ReadWrite'))
  try {
    for ($k = 0; $k -lt 40; $k++) {
      $l = $sr.ReadLine()
      if ($null -eq $l) { break }
      if ($l.Trim().StartsWith('{')) { try { return ($l | ConvertFrom-Json) } catch { } }
    }
  } finally { $sr.Close() }
  return $null
}

# --- lines that are machinery, not you ---------------------------------------
# NOTE: matched with .Contains(), NOT -like. '[Request interrupted' contains '[',
# which -like reads as a character-class opener and throws.
$noise = @(
  '<task-notification>', '<system-reminder>', 'Stop hook feedback',
  '[Request interrupted', 'PreToolUse:', 'PostToolUse:', '<local-command',
  'Caveat: The messages below', 'This session is being continued from',
  'Continue from where you left off', 'was loaded earlier',
  'BLOCKED by muhl_cite_gate', 'No response requested'
)
function Test-Noise([string]$t) {
  foreach ($n in $noise) { if ($t.Contains($n)) { return $true } }
  return $false
}

function Get-Text($content) {
  if ($content -is [string]) { return $content }
  if ($content) { return (($content | Where-Object { $_.type -eq 'text' } | ForEach-Object { $_.text }) -join ' ') }
  return ''
}

Write-Host ""
Write-Host "Scanning transcripts by REAL last activity (mtime is NOT trusted)..." -Foreground DarkGray

# --- candidate set: only files sitting DIRECTLY in a project dir --------------
# Anything under \subagents\ or \wf_*\ is a sidechain transcript, not a session.
$projDirs = Get-ChildItem $projRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notlike 'wf_*' -and $_.Name -ne 'subagents' }

$files = foreach ($d in $projDirs) {
  Get-ChildItem $d.FullName -Filter *.jsonl -File -ErrorAction SilentlyContinue
}

$totalOnDisk = (Get-ChildItem $projRoot -Recurse -Filter *.jsonl -File -ErrorAction SilentlyContinue).Count
Write-Host ("  {0} transcripts on disk; {1} sit directly in a project dir (the rest are subagent/workflow sidechains)" -f $totalOnDisk, $files.Count) -Foreground DarkGray

$rows = foreach ($f in $files) {
  $first = Get-FirstRecord $f.FullName
  if (-not $first) { continue }

  $isSide = [bool]$first.isSidechain
  if ($isSide -and -not $IncludeSidechains) { continue }

  # cwd is ground truth - never decode the directory name
  $cwd = $first.cwd

  $txt = Get-Tail $f.FullName $TailBytes
  $lines = $txt -split "`n" | Where-Object { $_.Trim().StartsWith('{') }

  $lastAny = $null; $lastTyped = $null; $typedTime = $null; $cwdLate = $null
  for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    try { $o = $lines[$i] | ConvertFrom-Json } catch { continue }
    if (-not $lastAny -and $o.timestamp) { $lastAny = $o.timestamp }
    if (-not $cwdLate -and $o.cwd) { $cwdLate = $o.cwd }   # cwd can change mid-session
    if (-not $lastTyped -and $o.type -eq 'user') {
      $t = Get-Text $o.message.content
      if ($t -and -not (Test-Noise $t)) {
        $lastTyped = ($t -replace '\s+', ' ').Trim()
        $typedTime = $o.timestamp
      }
    }
    if ($lastAny -and $lastTyped -and $cwdLate) { break }
  }
  if (-not $lastAny) { continue }
  if ($cwdLate) { $cwd = $cwdLate }

  [pscustomobject]@{
    LastActivity = [datetime]$lastAny
    LastTypedAt  = $(if ($typedTime) { [datetime]$typedTime } else { $null })
    LastTyped    = $lastTyped
    SessionId    = $f.BaseName
    Cwd          = $cwd
    SizeMB       = [math]::Round($f.Length / 1MB, 2)
    Sidechain    = $isSide
  }
}

$rows = $rows | Sort-Object LastActivity -Descending

if ($Days -gt 0) {
  $cut = (Get-Date).AddDays(-$Days)
  $rows = $rows | Where-Object { $_.LastTypedAt -and $_.LastTypedAt.ToLocalTime() -ge $cut }
}
if ($Match) {
  $rows = $rows | Where-Object {
    ($_.Cwd -and $_.Cwd.ToLower().Contains($Match.ToLower())) -or
    ($_.LastTyped -and $_.LastTyped.ToLower().Contains($Match.ToLower()))
  }
}

$shown = $rows | Select-Object -First $Top
if (-not $shown) { Write-Host "`n  no sessions matched.`n" -Foreground Yellow; exit 0 }

$n = 0
foreach ($r in $shown) {
  $n++
  $la = $r.LastActivity.ToLocalTime().ToString('yyyy-MM-dd HH:mm')
  $tt = if ($r.LastTypedAt) { $r.LastTypedAt.ToLocalTime().ToString('yyyy-MM-dd HH:mm') } else { '-' }

  # The tell that this row's recency is machinery, not you.
  $flag = ''
  if ($r.LastTypedAt -and ($r.LastActivity - $r.LastTypedAt).TotalHours -gt 12) {
    $flag = '   <-- recency is hook/agent noise, NOT your last turn'
  }

  Write-Host ""
  Write-Host ("[{0}] last activity {1}   (you last typed {2}){3}" -f $n, $la, $tt, $flag) -Foreground Cyan
  Write-Host ("     dir : {0}" -f $r.Cwd) -Foreground Gray
  Write-Host ("     size: {0} MB{1}" -f $r.SizeMB, $(if ($r.Sidechain) { '   [SIDECHAIN - not resumable]' } else { '' })) -Foreground DarkGray
  if ($r.LastTyped) {
    $snip = $r.LastTyped.Substring(0, [Math]::Min(160, $r.LastTyped.Length))
    Write-Host ("     you : {0}" -f $snip) -Foreground White
  } else {
    Write-Host ("     you : (no typed message found in the tail window)") -Foreground DarkYellow
  }
  if ($r.Sidechain) {
    Write-Host ("     (subagent/workflow transcript - cannot be resumed)") -Foreground DarkYellow
  } elseif ($r.Cwd -and (Test-Path $r.Cwd)) {
    Write-Host ("     RESUME: cd `"{0}`"; claude --resume {1}" -f $r.Cwd, $r.SessionId) -Foreground Green
  } else {
    Write-Host ("     RESUME: claude --resume {0}   (recorded cwd '{1}' no longer exists)" -f $r.SessionId, $r.Cwd) -Foreground Yellow
  }
}

Write-Host ""
Write-Host ("  {0} of {1} matching sessions shown. Copy a green RESUME line." -f $shown.Count, $rows.Count) -Foreground DarkGray
Write-Host ""
