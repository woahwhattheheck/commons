import json

def parse(raw):
    value = json.loads(raw)
    return value

def dump(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
