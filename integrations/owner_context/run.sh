#!/usr/bin/env bash
# Host-neutral always-on launcher. systemd/docker/compose also work.
# GitHub Actions is not an always-on owner-context host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
ENV_FILE="${COMMONS_OWNER_CONTEXT_ENV_FILE:-$ROOT/integrations/owner_context/.env.local}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
python3 host/owner_context.py doctor --json --no-probe
exec python3 integrations/owner_context/service.py serve
