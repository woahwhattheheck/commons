# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "route_realization_certificate", HERE / "route_realization_certificate.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def act(*market):
    return {"farmer": ["PASS"], "hands": [], "market": [list(r) for r in market]}


class RouteRealizationCertificateTests(unittest.TestCase):
    def test_counts_only_future_melon_sells_at_or_after_not_before(self):
        route = [
            act(("SELL", "MELON", 5)),
            act(("SELL", "MELON", 7)),
            act(("SELL", "WOOL", 99), ("SELL", "MELON", 11)),
        ]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=1
            ),
            18,
        )

    def test_current_step_also_bounds_capacity(self):
        route = [act(("SELL", "MELON", 5)), act(("SELL", "MELON", 7))]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=1, not_before_step=0
            ),
            7,
        )

    def test_rows_beyond_market_cap_are_not_credited(self):
        route = [act(
            ("SELL", "WOOL", 1),
            ("SELL", "MELON", 7),
            ("SELL", "MELON", 1000),
        )]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0, max_orders=2
            ),
            7,
        )

    def test_stop_before_step_excludes_unresolved_tail(self):
        route = [
            act(("SELL", "MELON", 2)),
            act(("SELL", "MELON", 3)),
            act(("SELL", "MELON", 100)),
        ]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0, stop_before_step=2
            ),
            5,
        )

    def test_not_before_at_or_after_stop_yields_zero(self):
        route = [act(("SELL", "MELON", 5)) for _ in range(4)]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=3, stop_before_step=3
            ),
            0,
        )

    def test_stop_bound_type_poison_fails_closed(self):
        route = [act(("SELL", "MELON", 5))]
        self.assertIsNone(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0, stop_before_step=True
            )
        )

    def test_non_melon_and_non_sell_rows_are_ignored(self):
        route = [act(
            ("SELL", "WOOL", 100),
            ("BUY_SEED", "MELON", 100),
            ("SELL", "MELON", 9),
        )]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0
            ),
            9,
        )

    def test_nonpositive_melon_sell_is_not_capacity(self):
        route = [act(("SELL", "MELON", 0)), act(("SELL", "MELON", -7))]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0
            ),
            0,
        )

    def test_type_poisoned_melon_quantity_fails_closed(self):
        for poison in (True, 3.0, "3", None):
            with self.subTest(poison=poison):
                route = [act(("SELL", "MELON", poison))]
                self.assertIsNone(
                    mod.explicit_melon_sell_capacity(
                        route, current_step=0, not_before_step=0
                    )
                )

    def test_type_poisoned_bounds_fail_closed(self):
        route = [act(("SELL", "MELON", 5))]
        for kwargs in (
            {"current_step": True, "not_before_step": 0},
            {"current_step": 0, "not_before_step": 1.0},
            {"current_step": 0, "not_before_step": 0, "max_orders": 0},
        ):
            with self.subTest(kwargs=kwargs):
                self.assertIsNone(mod.explicit_melon_sell_capacity(route, **kwargs))

    def test_malformed_executable_market_evidence_fails_closed(self):
        route = [{"market": [1]}]
        self.assertIsNone(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0
            )
        )

    def test_malformed_inert_suffix_row_is_ignored(self):
        route = [{"market": [["SELL", "MELON", 4], 1]}]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0, max_orders=1
            ),
            4,
        )

    def test_past_route_end_is_zero_but_beyond_route_is_invalid(self):
        route = [act(("SELL", "MELON", 4))]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=1, not_before_step=1
            ),
            0,
        )
        self.assertIsNone(
            mod.explicit_melon_sell_capacity(
                route, current_step=2, not_before_step=2
            )
        )

    def test_dynamic_or_terminal_capacity_is_deliberately_not_invented(self):
        route = [act(("SELL", "WOOL", 1)), act()]
        self.assertEqual(
            mod.explicit_melon_sell_capacity(
                route, current_step=0, not_before_step=0
            ),
            0,
        )

    def test_authenticated_source_executes_captured_bytes_not_reopened_path(self):
        fake = b"""TURNS = 720
MAX_ORDERS = 10
MAIN = "m"
YARN = "y"
YARN_CARROT = "c"
MILK_GLUT = "g"
DECISIONS = ((226, "f", 1, YARN), (360, "f", 1, YARN_CARROT), (433, "f", 1, MILK_GLUT))
def routes():
    def route():
        return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(TURNS)]
    return {MAIN: route(), YARN: route(), YARN_CARROT: route(), MILK_GLUT: route()}
"""
        expected = mod.git_blob_sha_bytes(fake)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "arlene.py"
            path.write_bytes(fake)
            original_read = Path.read_bytes
            swapped = {"done": False}

            def read_and_swap(self):
                data = original_read(self)
                if self == path and not swapped["done"]:
                    swapped["done"] = True
                    self.write_text('raise RuntimeError("reopened poisoned path")\n')
                return data

            with mock.patch.object(mod, "EXPECTED_ARLENE_BLOB", expected), mock.patch.object(
                Path, "read_bytes", read_and_swap
            ):
                routes, receipt = mod.load_authenticated_current_routes(path)

        self.assertTrue(swapped["done"])
        self.assertEqual(receipt["arlene_git_blob"], expected)
        self.assertEqual(len(routes["m"]), 720)

    def test_missing_current_source_fails_closed(self):
        packet = mod.current_route_melon_realization_certificate(
            route_id="missing",
            current_step=0,
            not_before_step=0,
            path=HERE / "does-not-exist.py",
        )
        self.assertIsNone(packet)

    @unittest.skipUnless(mod.ARLENE_PATH.exists(), "checkout current Arlene source unavailable")
    def test_exact_current_arlene_source_builds_authenticated_packet(self):
        routes, receipt = mod.load_authenticated_current_routes()
        self.assertEqual(receipt["arlene_git_blob"], mod.EXPECTED_ARLENE_BLOB)
        self.assertEqual(receipt["max_orders"], 10)
        self.assertTrue(routes)
        route_id = receipt["declared_route_ids"][0]
        packet = mod.current_route_melon_realization_certificate(
            route_id=route_id,
            current_step=0,
            not_before_step=0,
        )
        self.assertIsNotNone(packet)
        self.assertEqual(packet["arlene_git_blob"], mod.EXPECTED_ARLENE_BLOB)
        self.assertIsInstance(packet["certified_remaining_realization_units"], int)
        self.assertFalse(packet["credits_terminal_settlement"])


if __name__ == "__main__":
    unittest.main()
