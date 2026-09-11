import r04_full_router as r04
_ORIG_RESERVE = r04.reserve_sales

def _gated_reserve(action, view, state, tape, step):
    if int(step) >= 648:
        return None
    return _ORIG_RESERVE(action, view, state, tape, step)

r04.reserve_sales = _gated_reserve
_AGENT = r04.install(None, 8, 0, True, True, True, True)
def agent(observation, configuration=None):
    return _AGENT(observation, configuration)
