# Generate Changelog

A dependency-free Bash command for Claude Builders Bounty #1. It reads the current repository's Git history since the latest reachable tag, categorizes commit subjects into **Added / Fixed / Changed / Removed**, and writes a structured `CHANGELOG.md`. Merge commits are omitted.

## Setup and run

1. Copy `changelog.sh` into the root of the Git repository you want to summarize.
2. Run `chmod +x changelog.sh`.
3. Run `./changelog.sh` (or `bash changelog.sh`).

The latest reachable tag is selected with `git describe --tags --abbrev=0`. If the repository has no tags, the command falls back to all reachable commits. Conventional `feat`/add/create/implement subjects map to **Added**; fix/bugfix/repair subjects to **Fixed**; remove/delete/drop/deprecate subjects to **Removed**; everything else maps to **Changed**.

An optional first argument changes the output path, for example `./changelog.sh docs/CHANGELOG.md`.

## Real-repository sample

`SAMPLE_CHANGELOG.md` uses the live public `psf/requests` history from release tag `v2.34.2` through `main@dae7ef63b4df6eded86637f251fc4e3a06c3b479`. GitHub's compare API reports 28 commits in that range; the sample contains all 28 first-line subjects categorized by the same rules.
