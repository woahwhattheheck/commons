# Unit tests for the r04_fert_warehouse lane module. Run: python3 -B test_fert_warehouse.py
import sys
sys.path.insert(0, '.')
import fert_warehouse as F

passed = failed = 0
def check(name, cond):
    global passed, failed
    if cond: passed += 1
    else:
        failed += 1
        print('FAIL:', name)


priv = {'shed': {'FERTILIZER': 60, 'WHEAT': 30},
        'inventories': [{'FERTILIZER': 10}, {}]}
check('warehouse dump at floor+full shed',
      F.warehouse_dump_orders(priv, 1) == [['SELL', 'FERTILIZER', 60], ['SELL', 'FERTILIZER', 10]])
check('no dump when price high', F.warehouse_dump_orders(priv, 50) == [])
priv_roomy = {'shed': {'FERTILIZER': 60}, 'inventories': []}
check('no dump when shed roomy', F.warehouse_dump_orders(priv_roomy, 1) == [])
check('revenue mode at $100', F.decide(priv, 100)['mode'] == 'revenue')
check('warehouse mode at $1', F.decide(priv, 1)['mode'] == 'warehouse')
check('hold when poor and roomy', F.decide(priv_roomy, 10)['mode'] == 'hold')
check('OFF-identity: decide hold emits nothing',
      F.decide({'shed': {}, 'inventories': []}, 1) == {'mode': 'hold', 'orders': []})

print(f'{passed} passed, {failed} failed')
sys.exit(1 if failed else 0)

print('fert_warehouse: %d passed, %d failed' % (passed, failed))
raise SystemExit(1 if failed else 0)
