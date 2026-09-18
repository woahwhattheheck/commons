import importlib.util
import math
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("erdos366_extend", HERE / "erdos366_extend.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def brute_factor_counts(n: int):
    if n == 1:
        return ()
    out = []
    p = 2
    while p * p <= n:
        if n % p:
            p = 3 if p == 2 else p + 2
            continue
        e = 0
        while n % p == 0:
            n //= p
            e += 1
        out.append((p, e))
        p = 3 if p == 2 else p + 2
    if n > 1:
        out.append((n, 1))
    return tuple(out)


def brute_is_powerful(n: int) -> bool:
    if n == 1:
        return True
    return all(e >= 2 for _, e in brute_factor_counts(n))


def brute_k_full(n: int, k: int) -> bool:
    if n == 1:
        return True
    return all(e >= k for _, e in brute_factor_counts(n))


class ExtendTests(unittest.TestCase):
    def test_integer_roots_exact(self):
        for k in (2, 3, 4, 5):
            for n in range(0, 5000):
                r = mod.integer_nth_root(n, k)
                self.assertLessEqual(r ** k, n)
                self.assertGreater((r + 1) ** k, n)

    def test_miller_rabin_matches_trial_primality_small_range(self):
        for n in range(0, 20000):
            expected = n >= 2 and all(n % d for d in range(2, math.isqrt(n) + 1))
            self.assertEqual(expected, mod.is_prime64(n), n)
        for composite in (341550071728321, 3825123056546413051):
            self.assertFalse(mod.is_prime64(composite))

    def test_factorization_exact(self):
        values = [
            1,
            2,
            64,
            729,
            99991 * 99991,
            1_000_003 * 1_000_033,
            (999_983 ** 2) * 37,
            600_851_475_143,
        ]
        for n in values:
            fs = mod.factor_counts(n)
            self.assertEqual(n, mod.factors_product(fs))
            self.assertEqual(brute_factor_counts(n), fs)

    def test_powerful_classifier_matches_brute_force(self):
        trial = mod.primes_upto(97)
        for n in range(1, 100000):
            chk = mod.check_powerful(n, trial)
            self.assertEqual(brute_is_powerful(n), chk.is_powerful, n)
            if not chk.is_powerful:
                p = chk.rejecting_prime
                self.assertIsNotNone(p)
                self.assertEqual(0, n % p)
                self.assertNotEqual(0, n % (p * p))
            else:
                self.assertEqual(n, mod.factors_product(chk.factors))

    def test_three_full_enumerator_matches_bruteforce(self):
        bound = 100000
        expected = [n for n in range(2, bound + 1) if brute_k_full(n, 3)]
        actual = mod.enumerate_k_full_values(bound, 3)
        self.assertEqual(expected, actual)
        self.assertEqual(len(actual), len(set(actual)))

    def test_whole_search_matches_bruteforce_small(self):
        bound = 100000
        expected = []
        for m in range(2, bound + 1):
            if brute_k_full(m, 3) and brute_is_powerful(m - 1):
                expected.append((m - 1, m))
        got = mod.search(bound, trial_prime_limit=97)
        self.assertEqual(len(expected), got["witness_count"])
        self.assertEqual(expected, [(x["n"], x["n_plus_1"]) for x in got["witnesses"]])

    def test_landed_1e12_bounded_result_is_reproduced(self):
        got = mod.search(1_000_000_000_000)
        self.assertEqual(41135, got["global_3full_successors"])
        self.assertEqual(41135, got["selected_3full_successors"])
        self.assertEqual(0, got["witness_count"])

    def test_shards_partition_candidate_ordinals(self):
        bound = 10_000_000
        whole = mod.enumerate_k_full_values(bound, 3)
        count = 4
        seen = []
        total = 0
        for index in range(count):
            got = mod.search(bound, shard_index=index, shard_count=count, trial_prime_limit=97)
            total += got["selected_3full_successors"]
            seen.extend(range(index, len(whole), count))
        self.assertEqual(len(whole), total)
        self.assertEqual(list(range(len(whole))), sorted(seen))

    def test_digest_is_deterministic(self):
        a = mod.search(100_000_000, trial_prime_limit=97)
        b = mod.search(100_000_000, trial_prime_limit=97)
        self.assertEqual(a["record_digest_sha256"], b["record_digest_sha256"])
        self.assertEqual(a["classification_counts"], b["classification_counts"])


if __name__ == "__main__":
    unittest.main()
