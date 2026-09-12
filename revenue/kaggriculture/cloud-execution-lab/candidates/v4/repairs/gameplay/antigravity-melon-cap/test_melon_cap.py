# Unit tests for the r04_melon_cap lane module. Run: python3 -B test_melon_cap.py
import sys
sys.path.insert(0, '.')
import melon_cap as M

passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond: passed += 1
    else:
        failed += 1
        print('FAIL:', name)

# --- melon cap ---
obs = {'player': 0, 'step': 600,
       'farms': [{'sale_counters': {'MELON': 0}}],
       'market': {'inventory': {'MELON': 9976}}}  # 10000 - 24 town-eaten
check('fresh game: 28 unit budget -> 4 plants', M.max_melon_plants(obs) == 4)
check('remaining budget 28', M.remaining_melon_budget(obs) == 28)

props = [{'crop': 'MELON', 'tiles': list(range(25)), 'seed_units': 25},
         {'crop': 'CARROT', 'tiles': list(range(25))}]
out = M.filter_proposals(props, obs)
check('melon proposal shrunk to budget', len(out[0]['tiles']) == 4)
check('carrot untouched', out[1]['crop'] == 'CARROT' and len(out[1]['tiles']) == 25)

obs_over = {'player': 0, 'step': 600,
            'farms': [{'sale_counters': {'MELON': 30}}],
            'market': {'inventory': {'MELON': 10006}}}
check('over budget: melon dropped', M.filter_proposals(props, obs_over) == [props[1]])
check('blocked count', M.plants_blocked(obs_over, 25) == 25)

# inventory-drift fallback (no sale_counters)
obs_drift = {'player': 0, 'step': 600, 'farms': [{}],
             'market': {'inventory': {'MELON': 10010}}}
check('drift fallback: 10010-10000+25 town-eaten = 35 sold', M.lifetime_melon_sold(obs_drift) == 35)


print('melon_cap: %d passed, %d failed' % (passed, failed))
raise SystemExit(1 if failed else 0)
