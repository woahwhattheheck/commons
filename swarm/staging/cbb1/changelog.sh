#!/usr/bin/env bash
set -euo pipefail

if ! repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  echo "generate-changelog: run this command inside a Git repository" >&2
  exit 2
fi

cd "$repo_root"
output="${1:-CHANGELOG.md}"
latest_tag="$(git describe --tags --abbrev=0 2>/dev/null || true)"

if [ -n "$latest_tag" ]; then
  range="$latest_tag..HEAD"
  source_note="Generated from commits after tag `$latest_tag`."
else
  range="HEAD"
  source_note="Generated from all reachable commits because this repository has no tags."
fi

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/generate-changelog.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM

: >"$tmpdir/added"
: >"$tmpdir/fixed"
: >"$tmpdir/changed"
: >"$tmpdir/removed"

git log --no-merges --format='%h%x09%s' "$range" |
while IFS=$'\t' read -r hash subject; do
  [ -n "$hash" ] || continue
  lower="$(printf '%s' "$subject" | tr '[:upper:]' '[:lower:]')"

  case "$lower" in
    feat:*|feat\(*|add\ *|add:*|added\ *|create\ *|create:*|implement\ *|implement:*|introduce\ *|introduce:*|new\ *)
      section="added"
      ;;
    fix\ *|fix:*|fix\(*|fixed\ *|bugfix*|hotfix*|patch\ *|patch:*|resolve\ *|resolve:*|repair\ *|repair:*)
      section="fixed"
      ;;
    remove\ *|remove:*|removed\ *|delete\ *|delete:*|drop\ *|drop:*|deprecate\ *|deprecate:*)
      section="removed"
      ;;
    *)
      section="changed"
      ;;
  esac

  printf -- '- %s (`%s`)\n' "$subject" "$hash" >>"$tmpdir/$section"
done

emit_section() {
  heading="$1"
  file="$2"
  printf '### %s\n\n' "$heading"
  if [ -s "$file" ]; then
    cat "$file"
  else
    printf -- '- None.\n'
  fi
  printf '\n'
}

{
  printf '# Changelog\n\n'
  printf '%s\n\n' "$source_note"
  printf '## [Unreleased]\n\n'
  emit_section "Added" "$tmpdir/added"
  emit_section "Fixed" "$tmpdir/fixed"
  emit_section "Changed" "$tmpdir/changed"
  emit_section "Removed" "$tmpdir/removed"
} >"$tmpdir/CHANGELOG.md"

mv "$tmpdir/CHANGELOG.md" "$output"
printf 'Wrote %s\n' "$repo_root/$output"
