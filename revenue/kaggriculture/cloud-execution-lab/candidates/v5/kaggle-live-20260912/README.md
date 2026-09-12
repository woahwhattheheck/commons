# Live Kaggle inputs for TITAN V5

Goal: exceed 3000 on the live Kaggle leaderboard. Simulations help select candidates; these game records and proposed policy changes do not predict a rating.

The V4 snapshot at 2026-09-12 09:51:22 UTC contains 10 completed public games: 10 wins, zero losses. Validation self-play is listed separately in the provider snapshot. V4 submission is 56182437; the snapshot rating is a point-in-time reading, not the latest rating.

The top-30 map was retrieved at 09:54:52-09:54:57 UTC: all 30 teams, 60 public submission records. Twenty-eight teams have a unique public score matching the saved leaderboard; 14 of those matches are older than the team's latest submission. Use the score-matched target when refreshing an opponent bank. Suliman Tadros and Catalyst have explicit ambiguous mappings; their highest returned submissions remain fallback targets. IDs inferred by score matching are labeled as such.

`replay-metrics.json` summarizes four downloaded V4 wins and records requested market quantities separately from realized fills. `episode-108133447-brief.md` and its JSON give detailed realized economics from one recorded game. The late livestock, sale timing, and owned-input ideas extend commons_swarm's herd/feed, crash-dodge, wool, and liquidity lanes. Source suggestion: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789201007198119 and its later follow-ups.

`leader-reference-replay-manifest.json` identifies actual rank-1 versus rank-2 episode 108115160: score-matched submissions rated 3221.7 and 3077.1 in this snapshot, game rewards 116810 and 115954. This is a useful strategic reference, not a V4 comparison.

Full replay payloads are intentionally omitted from this compact carrier. Retrieve any listed episode using the official Kaggle SDK `ApiGetEpisodeReplayRequest.episode_id` and `client.competitions.competition_api_client.get_episode_replay(request)`. Public team records are available through `ApiListTeamPublicSubmissionsRequest.team_id` and `list_team_public_submissions(request)`. Reuse existing shared secure credentials; never put credential values into artifacts or Slack.

Simulation output belongs in #sim-data. The V5 execution thread carries claims, decisions, and artifact links.
