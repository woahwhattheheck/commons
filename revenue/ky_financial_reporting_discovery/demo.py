from .parity_probe import compare_rows

def run_demo():
    return compare_rows([{"id":"A","value":1}], [{"id":"A","value":2}], ["id"], ["value"])
