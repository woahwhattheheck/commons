#!/usr/bin/env python3
"""Independent stdlib audit of reconstructible claims in arXiv:2609.04686v1.

This does NOT verify the archived DRAT proofs. It rebuilds only objects specified
completely in the paper: the Tutte-Coxeter labeling, the repaired u-edge
orientation, and the H15 gadget.
"""
from collections import Counter, deque


def add_edge(g, a, b):
    g.setdefault(a, set()).add(b)
    g.setdefault(b, set()).add(a)


def canonical_cycle(cycle):
    n = len(cycle)
    variants = []
    for seq in (cycle, list(reversed(cycle))):
        for i in range(n):
            variants.append(tuple(seq[i:] + seq[:i]))
    return min(variants)


def cycles_exact(g, length):
    seen = set()
    for start in sorted(g, key=str):
        stack = [(start, [start], {start})]
        while stack:
            v, path, used = stack.pop()
            if len(path) == length:
                if start in g[v]:
                    seen.add(canonical_cycle(path))
                continue
            for w in g[v]:
                if w == start or w in used:
                    continue
                # Works for homogeneous int or str vertex sets used below and
                # removes duplicate searches by forcing start to be minimum.
                if str(w) < str(start):
                    continue
                stack.append((w, path + [w], used | {w}))
    return seen


def cycle_neighbors(cycle, x):
    i = cycle.index(x)
    return {cycle[(i - 1) % len(cycle)], cycle[(i + 1) % len(cycle)]}


def is_bipartite(g):
    color = {}
    for start in g:
        if start in color:
            continue
        color[start] = 0
        q = deque([start])
        while q:
            v = q.popleft()
            for w in g[v]:
                if w not in color:
                    color[w] = 1 - color[v]
                    q.append(w)
                elif color[w] == color[v]:
                    return False
    return True


def tutte_coxeter():
    g = {i: set() for i in range(30)}
    for i in range(30):
        add_edge(g, i, (i + 1) % 30)
    for t in range(5):
        for a, b in (
            ((29 + 6 * t) % 30, (12 + 6 * t) % 30),
            ((28 + 6 * t) % 30, (7 + 6 * t) % 30),
            ((26 + 6 * t) % 30, (3 + 6 * t) % 30),
        ):
            add_edge(g, a, b)
    return g


def h7(prefix):
    g = {prefix + x: set() for x in "uvwabcd"}
    for a, b in (
        ("v", "a"), ("a", "b"), ("b", "w"), ("c", "v"),
        ("w", "d"), ("a", "c"), ("c", "u"), ("u", "d"), ("d", "b"),
    ):
        add_edge(g, prefix + a, prefix + b)
    return g


def h15():
    g = {}
    for part in (h7("A"), h7("B")):
        for v, ns in part.items():
            g.setdefault(v, set()).update(ns)
    g["z"] = set()
    add_edge(g, "Av", "Bv")
    add_edge(g, "Aw", "z")
    add_edge(g, "z", "Bw")
    return g, {"u": "z", "v": "Bu", "w": "Au"}


def simple_path_lengths(g, start, target):
    lengths = set()
    stack = [(start, [start], {start})]
    while stack:
        v, path, used = stack.pop()
        if v == target:
            lengths.add(len(path) - 1)
            continue
        for w in g[v]:
            if w not in used:
                stack.append((w, path + [w], used | {w}))
    return lengths


def main():
    tc = tutte_coxeter()
    assert set(Counter(map(len, tc.values()))) == {3}
    assert is_bipartite(tc)
    for length in range(3, 8):
        assert not cycles_exact(tc, length), length
    c8 = cycles_exact(tc, 8)
    assert len(c8) == 90, len(c8)

    alternating = canonical_cycle([0, 17, 18, 5, 6, 23, 22, 1])
    assert alternating in c8
    outer = {frozenset((i, (i + 1) % 30)) for i in range(30)}
    chord_neighbor = {}
    for v in range(30):
        chords = [w for w in tc[v] if frozenset((v, w)) not in outer]
        assert len(chords) == 1
        chord_neighbor[v] = chords[0]
    assert all(
        chord_neighbor[v] in cycle_neighbors(list(alternating), v)
        for v in alternating
    )

    # Appendix A table: neighbor y whose edge xy faces attachment u.
    u_neighbor = {
        0: 1, 5: 4, 10: 9, 15: 8, 20: 19, 25: 16,
        1: 0, 6: 5, 11: 10, 16: 15, 21: 14, 26: 3,
        2: 1, 7: 6, 12: 11, 17: 0, 22: 1, 27: 20,
        3: 2, 8: 7, 13: 4, 18: 19, 23: 6, 28: 7,
        4: 3, 9: 2, 14: 13, 19: 20, 24: 11, 29: 28,
    }
    assert set(u_neighbor) == set(range(30))
    assert all(u_neighbor[v] in tc[v] for v in range(30))
    off_counts = []
    for cycle_tuple in c8:
        cycle = list(cycle_tuple)
        off = [
            v for v in cycle
            if u_neighbor[v] not in cycle_neighbors(cycle, v)
        ]
        assert off, cycle
        off_counts.append(len(off))

    gadget, attachment = h15()
    assert len(gadget) == 15
    assert Counter(map(len, gadget.values())) == Counter({3: 12, 2: 3})
    uv = simple_path_lengths(gadget, attachment["u"], attachment["v"])
    uw = simple_path_lengths(gadget, attachment["u"], attachment["w"])
    vw = simple_path_lengths(gadget, attachment["v"], attachment["w"])
    assert uv == uw == set(range(3, 15))
    assert vw == set(range(5, 15))
    spectrum = {length for length in range(3, 16) if cycles_exact(gadget, length)}
    assert spectrum == {3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15}
    assert not ({4, 8} & spectrum)

    print("PASS: paper-specified construction audit")
    print("Tutte-Coxeter: 30 vertices, cubic, bipartite, girth 8")
    print("8-cycles:", len(c8))
    print("alternating Exoo-counterexample cycle: present")
    print("repaired orientation: every 8-cycle has >=1 off-cycle u-edge")
    print("off-cycle u-edge count distribution:", dict(sorted(Counter(off_counts).items())))
    print("H15 u-v/u-w path lengths: 3..14; v-w: 5..14")
    print("H15 cycle spectrum:", sorted(spectrum))
    print("DRAT archive bytes/proofs: NOT VERIFIED BY THIS SCRIPT")


if __name__ == "__main__":
    main()
