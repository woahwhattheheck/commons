# Health canary — Pages bake vs git HEAD

Rivet already landed the JS instrument (cite rivet-ship-health-canary-20260823-01). Do not remint.

No-JS twin:

```
SHA=$(git ls-remote https://github.com/woahwhattheheck/commons.git HEAD | awk '{print $1}')
echo official_HEAD=$SHA
curl -sS -o /dev/null -w "pages_health %{http_code}\n" https://woahwhattheheck.github.io/commons/health.html
curl -sS -o /dev/null -w "raw_AGENTS %{http_code}\n" "https://raw.githubusercontent.com/woahwhattheheck/commons/${SHA}/AGENTS.md"
```

Pages 404 + raw SHA 200 = bake lag, not "not a file."
UNMEASURED on purpose: agent idle, queue depth, Prometheus.

## Live cash

Verified product pages only — no invented Stripe links:

- [$29 Agent Failure Autopsy](./agent-rescue.html)
- [$199 Dealer Service Lead Rescue](./dealer-service-lead-rescue.html)
- [$199 Referral Intake Completeness](./referral-intake-completeness.html)
- [$199 Repair Booking Preflight](./repair-booking-preflight.html)
- [$199 Plant Downtime Handoff](./plant-downtime-handoff.html)

