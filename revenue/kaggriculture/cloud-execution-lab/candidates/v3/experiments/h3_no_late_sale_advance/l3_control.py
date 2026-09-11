import r04_full_router as r04
_AGENT = r04.install(None, 8, 0, True, True, True, True)
def agent(observation, configuration=None):
    return _AGENT(observation, configuration)
