"""Commercial console boundary.

This module has no access to case records, source material, analysis services,
review decisions, or release controls.  Its inputs are limited to account-level
licensing metadata.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CommercialConsole:
    organization_label: str = ""
    license_reference: Optional[str] = None
    seat_count: int = 1

    def update_license(
        self,
        organization_label: str,
        license_reference: str,
        seat_count: int,
    ) -> None:
        if seat_count < 1:
            raise ValueError("Seat count must be positive.")
        self.organization_label = organization_label.strip()
        self.license_reference = license_reference.strip() or None
        self.seat_count = seat_count

    def snapshot(self) -> Dict[str, object]:
        return {
            "organization_label": self.organization_label,
            "license_reference": self.license_reference,
            "seat_count": self.seat_count,
        }
