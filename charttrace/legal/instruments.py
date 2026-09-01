"""Versioned ChartTrace legal and data-use instruments.

The application ships these instruments locally.  They are deliberately plain
text so the Trust Center remains available before unlock and without network
access.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple


TRUST_CENTER_VERSION = "1.1"


@dataclass(frozen=True)
class LegalInstrument:
    instrument_id: str
    title: str
    version: str
    acknowledgement: str
    body: str


INSTRUMENTS: Tuple[LegalInstrument, ...] = (
    LegalInstrument(
        "terms",
        "Terms of Service",
        "1.1",
        "I have read and agree to the Terms of Service.",
        (
            "ChartTrace is a local evidence-organization tool. It does not "
            "provide legal advice, decide claims, or replace attorney review. "
            "The operator remains responsible for lawful use, source accuracy, "
            "deadlines, and every released statement."
        ),
    ),
    LegalInstrument(
        "privacy_data_use",
        "Privacy and Data-Use Notice",
        "1.1",
        "I acknowledge the Privacy and Data-Use Notice.",
        (
            "Case material is processed in the local application data store. "
            "ChartTrace v1.1 includes no analytics, advertising, telemetry, "
            "external fonts, or automatic cloud transfer. Export occurs only "
            "through an explicit operator action."
        ),
    ),
    LegalInstrument(
        "authority",
        "Authority and Lawful-Possession Attestation",
        "1.1",
        "I attest that I am authorized and lawfully possess the material.",
        (
            "The operator attests that they are authorized to process each "
            "source and lawfully possess it. Analysis is unavailable while "
            "authority is absent, disputed, expired, or placed on hold."
        ),
    ),
    LegalInstrument(
        "peer_ai_disclosure",
        "Peer/AI Analysis and Human-Review Disclosure",
        "1.1",
        "I acknowledge the peer/AI and mandatory human-review disclosure.",
        (
            "Automated and peer outputs may be incomplete, inaccurate, or "
            "hallucinated. They are hypotheses, not findings. A qualified human "
            "must inspect sources, citations, conflicts, and scope before release."
        ),
    ),
    LegalInstrument(
        "retention_export_deletion",
        "Retention, Export, and Deletion Policy",
        "1.1",
        "I acknowledge the retention, export, and deletion controls.",
        (
            "The operator selects retention and controls exports. Deletion is "
            "recorded with a local receipt; an authorized retention hold blocks "
            "deletion until removed. Exported copies are outside local deletion."
        ),
    ),
    LegalInstrument(
        "recipient_transfer",
        "Recipient/Attorney Transfer Authorization",
        "1.1",
        "I acknowledge that each named recipient requires separate authorization.",
        (
            "Acceptance does not authorize transfer. Transfer is off by default "
            "and must be affirmatively authorized for a named recipient. Changing "
            "that recipient revokes prior authorization."
        ),
    ),
    LegalInstrument(
        "roles_compensation",
        "Counsel/Affiliate Role and Compensation Disclosures",
        "1.1",
        "I acknowledge the counsel, affiliate, role, and compensation disclosures.",
        (
            "The operator must disclose relevant counsel and affiliate roles, "
            "referral relationships, financial interests, and compensation. "
            "Commercial status cannot alter evidence, analysis, or review output."
        ),
    ),
)


def instrument_map() -> Dict[str, LegalInstrument]:
    return {instrument.instrument_id: instrument for instrument in INSTRUMENTS}


def instrument_versions(
    instruments: Iterable[LegalInstrument] = INSTRUMENTS,
) -> Dict[str, str]:
    return {
        instrument.instrument_id: instrument.version for instrument in instruments
    }


def instrument_suite_hash(
    instruments: Iterable[LegalInstrument] = INSTRUMENTS,
) -> str:
    """SHA-256 of the current local instrument suite. No production crypto claim."""
    canonical = json.dumps(
        [
            {
                "acknowledgement": instrument.acknowledgement,
                "body": instrument.body,
                "instrument_id": instrument.instrument_id,
                "title": instrument.title,
                "version": instrument.version,
            }
            for instrument in instruments
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
