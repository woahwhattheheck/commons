from __future__ import annotations

import importlib
import unittest

from revenue.pursuit_portfolio import current
from revenue.pursuit_portfolio.core import PortfolioError
from test_pursuit_portfolio_current import KEY


class ReplayFacadeTests(unittest.TestCase):
    def test_caller_key_current_names_fail_closed_after_reload(self):
        for module in (current, importlib.reload(current)):
            with self.assertRaisesRegex(
                PortfolioError, "fixed-host fresh-process boundary"
            ):
                module.compile_authorized_current({}, {}, KEY)
            with self.assertRaisesRegex(
                PortfolioError, "fixed-host fresh-process boundary"
            ):
                module.verify_authorized_current(b"", b"", b"", b"", b"", KEY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
