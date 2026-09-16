from __future__ import annotations

import subprocess
import sys
import unittest


MODULES = (
    "revenue.service_deal_economics.test_engine",
    "revenue.service_deal_economics.test_authority",
    "revenue.service_deal_economics.test_authority_surface",
)


class ServiceDealEconomicsBatteryBridge(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", *MODULES])
        subprocess.run(command, check=True)

    def test_service_deal_economics_normal(self) -> None:
        self._run(False)

    def test_service_deal_economics_optimized(self) -> None:
        self._run(True)


if __name__ == "__main__":
    unittest.main()
