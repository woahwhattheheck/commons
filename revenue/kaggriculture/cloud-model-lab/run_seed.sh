#!/usr/bin/env bash
# Seeding launcher that records its own PID and exit status, so a later step can
# read a fact instead of guessing from a process-name substring. A `pgrep -f
# seed_bank.py` waiter matches its OWN command line and every sibling waiter, so
# such loops can never exit; that deadlocked four shells and blocked the A/B.
set -u
BANK="$1"; shift
STATUS_FILE="${BANK%.jsonl}.status.json"
echo "{\"pid\": $$, \"state\": \"running\"}" > "$STATUS_FILE"
rc=0
for T in "$@"; do
  /home/user/work/venv/bin/python -B seed_bank.py --bank "$BANK" \
    --seeds 4242001,5150011 --teacher "$T" --seat 0 --max-steps 300 \
    --exclude-seeds 7700001,8800001,9900017,3131017,6060013 || rc=$?
done
echo "{\"pid\": $$, \"state\": \"done\", \"exit\": $rc}" > "$STATUS_FILE"
exit $rc
