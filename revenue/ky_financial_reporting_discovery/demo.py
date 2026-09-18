from .parity_probe import compare_rows

def run_demo():
    before = [{"id":"A","value":10},{"id":"B","value":20}]
    after = [{"id":"A","value":10},{"id":"B","value":21}]
    return compare_rows(before, after, ["id"], ["value"])

if __name__ == "__main__":
    print(run_demo())
