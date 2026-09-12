# INTEGRATION-SPEC — r04_melon_cap

Source: verified vs pinned official `kaggriculture.py` 2026-09-12 (see module docstrings).
Status: 14/14 unit tests green in normal Python and `-O`. Default-OFF; OFF == base.

## Lane 1: r04_melon_cap — `r04-melon-cap/melon_cap.py`

Config flag: `r04_melon_cap` (boolean, default false; require actual bool).

Hook point: end of `fourth_quadrant.proposals()`, just before `return answer`:

```python
if configuration.get('r04_melon_cap') is True:
    answer = melon_cap.filter_proposals(answer, observation)
```

Any other code path that emits `['PLANT', 'MELON', ...]` should pass its
planned plant count through `melon_cap.plants_blocked(observation, n)` and
refuse that many. The module never changes non-melon proposals.

TITAN-CONFIG.json: add `"r04_melon_cap": false`.

