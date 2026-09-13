#!/usr/bin/env python3
"""Bind every dedicated checkout-first landing page to its canonical rail.

The capability projector proves provider, catalog, and funnel state. This
regression closes the last public-surface gap: a dedicated product page must
either expose exactly its canonical Stripe rail(s), or declare exact
catalog-driven checkout slots, and it must preserve the public delivery route.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
CATALOG = Path("revenue/outcome_commerce/catalog.json")
SNAPSHOT = Path("revenue/checkout_capability/snapshot.json")
CONTACT_PREFIX = "mailto:tokenjunkielabs@gmail.com"
STRIPE_HOSTS = {"buy.stripe.com", "donate.stripe.com"}
STRIPE_PATH = re.compile(r"/[A-Za-z0-9_-]+")
GENERIC_CATALOG_SURFACES = {"commerce.html", "pay.html", "tips.html"}


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.checkout_slots: list[str] = []
        self.script_srcs: list[str] = []

    def _consume(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])
        classes = set(values.get("class", "").split())
        if "js-checkout-slot" in classes:
            self.checkout_slots.append(values.get("data-sku", ""))
        if tag == "script" and values.get("src"):
            self.script_srcs.append(values["src"])

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._consume(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._consume(tag, attrs)


def _load(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def stripe_rail_key(raw: str) -> str | None:
    """Return the immutable provider origin/path identity; ignore tracking query."""
    try:
        parsed = urlsplit(unescape(str(raw).strip()))
        port = parsed.port
    except (TypeError, ValueError):
        return None
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() != "https"
        or host not in STRIPE_HOSTS
        or parsed.username
        or parsed.password
        or port is not None
        or not STRIPE_PATH.fullmatch(parsed.path)
    ):
        return None
    return f"https://{host}{parsed.path}"


def _local_html_route(raw: object) -> tuple[str | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "qualification.route must be a non-empty local HTML path"
    parsed = urlsplit(raw.strip())
    if parsed.scheme or parsed.netloc or parsed.query:
        return None, f"qualification.route must stay local and query-free: {raw}"
    path = parsed.path
    while path.startswith("./"):
        path = path[2:]
    pure = PurePosixPath(path)
    if not path or path.startswith("/") or ".." in pure.parts or pure.suffix.lower() != ".html":
        return None, f"qualification.route must be a safe local HTML path: {raw}"
    return pure.as_posix(), None


def dedicated_checkout_surfaces(root: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Map dedicated local page -> {sku: canonical_url} for public checkout-first SKUs."""
    catalog = _load(root, CATALOG)
    snapshot = _load(root, SNAPSHOT)
    errors: list[str] = []
    listings = {
        row.get("id"): row
        for row in catalog.get("listings") or []
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    rails: dict[str, dict] = {}
    for rail in snapshot.get("canonical_rails") or []:
        if not isinstance(rail, dict) or not isinstance(rail.get("sku"), str):
            continue
        sku = rail["sku"]
        if sku in rails:
            errors.append(f"duplicate canonical rail for {sku}")
            continue
        rails[sku] = rail

    surfaces: dict[str, dict[str, str]] = defaultdict(dict)
    funnels = catalog.get("funnels") if isinstance(catalog.get("funnels"), dict) else {}
    for sku, funnel in sorted(funnels.items()):
        if not isinstance(funnel, dict) or funnel.get("readiness") != "READY_FOR_CHECKOUT":
            continue
        listing = listings.get(sku)
        if not isinstance(listing, dict):
            errors.append(f"{sku}: READY_FOR_CHECKOUT listing missing")
            continue
        checkout = listing.get("checkout") if isinstance(listing.get("checkout"), dict) else {}
        required_checkout = (
            checkout.get("status") == "ACTIVE_CHARGEABLE"
            and checkout.get("provider") == "stripe"
            and checkout.get("link_active") is True
            and checkout.get("account_charges_enabled") is True
            and checkout.get("account_payouts_enabled") is True
            and isinstance(checkout.get("url"), str)
        )
        if not required_checkout:
            errors.append(f"{sku}: READY_FOR_CHECKOUT listing is not an active proven Stripe checkout")
            continue
        rail = rails.get(sku)
        if not isinstance(rail, dict):
            errors.append(f"{sku}: canonical rail missing")
            continue
        if (
            rail.get("exposure") != "CHECKOUT_FIRST"
            or rail.get("link_active") is not True
            or rail.get("livemode") is not True
            or rail.get("url") != checkout.get("url")
        ):
            errors.append(f"{sku}: canonical rail does not match the active catalog checkout")
            continue
        qualification = funnel.get("qualification") if isinstance(funnel.get("qualification"), dict) else {}
        route, route_error = _local_html_route(qualification.get("route"))
        if route_error:
            errors.append(f"{sku}: {route_error}")
            continue
        assert route is not None
        if route in GENERIC_CATALOG_SURFACES:
            continue
        surfaces[route][sku] = checkout["url"]
    return dict(surfaces), errors


def landing_surface_errors(root: Path) -> list[str]:
    surfaces, errors = dedicated_checkout_surfaces(root)
    if not surfaces:
        errors.append("no dedicated checkout-first HTML surfaces were derived")
        return errors

    root_resolved = root.resolve()
    for route, expected_by_sku in sorted(surfaces.items()):
        page = (root / route).resolve()
        if root_resolved != page and root_resolved not in page.parents:
            errors.append(f"{route}: resolved outside repository root")
            continue
        if not page.is_file():
            errors.append(f"{route}: dedicated checkout page missing")
            continue
        text = page.read_text(encoding="utf-8")
        parser = SurfaceParser()
        try:
            parser.feed(text)
            parser.close()
        except Exception as exc:  # HTMLParser errors should become deterministic evidence.
            errors.append(f"{route}: HTML parse failed: {exc}")
            continue

        expected_rails = {stripe_rail_key(url) for url in expected_by_sku.values()}
        if None in expected_rails:
            errors.append(f"{route}: catalog contains a malformed canonical Stripe URL")
            expected_rails.discard(None)
        actual_rails = {
            key for key in (stripe_rail_key(href) for href in parser.hrefs) if key is not None
        }
        slots = Counter(parser.checkout_slots)
        has_pay_js = any(PurePosixPath(urlsplit(src).path).name == "pay.js" for src in parser.script_srcs)

        if actual_rails and slots:
            errors.append(f"{route}: mixes raw Stripe anchors with catalog checkout slots")
        elif actual_rails:
            if actual_rails != expected_rails:
                errors.append(
                    f"{route}: Stripe rails {sorted(actual_rails)} do not equal canonical rails "
                    f"{sorted(expected_rails)}"
                )
        elif slots:
            expected_skus = set(expected_by_sku)
            if set(slots) != expected_skus or any(count != 1 for count in slots.values()):
                errors.append(
                    f"{route}: checkout slots {dict(sorted(slots.items()))} do not bind exactly once "
                    f"to {sorted(expected_skus)}"
                )
            if not has_pay_js:
                errors.append(f"{route}: catalog checkout slots require pay.js")
        else:
            errors.append(f"{route}: no canonical Stripe anchor or catalog checkout slot")

        if not any(href.lower().startswith(CONTACT_PREFIX) for href in parser.hrefs):
            errors.append(f"{route}: canonical Token Junkie Labs handoff mailto missing")
    return errors


class CheckoutLandingIntegrity(unittest.TestCase):
    def test_current_tree_binds_dedicated_pages_to_canonical_rails(self) -> None:
        self.assertEqual(landing_surface_errors(ROOT), [])

    @staticmethod
    def _fixture(root: Path, rows: list[tuple[str, str, str]], pages: dict[str, str]) -> None:
        (root / CATALOG.parent).mkdir(parents=True, exist_ok=True)
        (root / SNAPSHOT.parent).mkdir(parents=True, exist_ok=True)
        listings = []
        funnels = {}
        rails = []
        for sku, route, url in rows:
            listings.append({
                "id": sku,
                "checkout": {
                    "status": "ACTIVE_CHARGEABLE",
                    "provider": "stripe",
                    "url": url,
                    "link_active": True,
                    "account_charges_enabled": True,
                    "account_payouts_enabled": True,
                },
            })
            funnels[sku] = {
                "readiness": "READY_FOR_CHECKOUT",
                "qualification": {"route": route},
            }
            rails.append({
                "sku": sku,
                "url": url,
                "link_active": True,
                "livemode": True,
                "exposure": "CHECKOUT_FIRST",
            })
        (root / CATALOG).write_text(json.dumps({"listings": listings, "funnels": funnels}), encoding="utf-8")
        (root / SNAPSHOT).write_text(json.dumps({"canonical_rails": rails}), encoding="utf-8")
        for route, text in pages.items():
            (root / route).write_text(text, encoding="utf-8")

    def test_static_anchor_accepts_tracking_but_rejects_foreign_rail(self) -> None:
        canonical = "https://buy.stripe.com/canonical_1"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(
                root,
                [("sku-one", "one.html", canonical)],
                {"one.html": '<a href="https://buy.stripe.com/canonical_1?utm_source=commons">buy</a>'
                             '<a href="mailto:tokenjunkielabs@gmail.com?subject=one">handoff</a>'},
            )
            self.assertEqual(landing_surface_errors(root), [])
            (root / "one.html").write_text(
                '<a href="https://buy.stripe.com/foreign_2">wrong</a>'
                '<a href="mailto:tokenjunkielabs@gmail.com">handoff</a>',
                encoding="utf-8",
            )
            errors = landing_surface_errors(root)
            self.assertTrue(any("do not equal canonical rails" in row for row in errors), errors)

    def test_shared_dynamic_surface_requires_exact_slots_pay_js_and_mailto(self) -> None:
        rows = [
            ("sku-a", "shared.html", "https://buy.stripe.com/a_1"),
            ("sku-b", "shared.html", "https://buy.stripe.com/b_2"),
        ]
        good = (
            '<div class="js-checkout-slot" data-sku="sku-a"></div>'
            '<div class="js-checkout-slot" data-sku="sku-b"></div>'
            '<a href="mailto:tokenjunkielabs@gmail.com?subject=shared">handoff</a>'
            '<script src="./pay.js?v=1"></script>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, rows, {"shared.html": good})
            self.assertEqual(landing_surface_errors(root), [])
            (root / "shared.html").write_text(good.replace('<script src="./pay.js?v=1"></script>', ""), encoding="utf-8")
            errors = landing_surface_errors(root)
            self.assertIn("shared.html: catalog checkout slots require pay.js", errors)

    def test_missing_delivery_route_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(
                root,
                [("sku-one", "one.html", "https://buy.stripe.com/canonical_1")],
                {"one.html": '<a href="https://buy.stripe.com/canonical_1">buy</a>'},
            )
            errors = landing_surface_errors(root)
            self.assertIn("one.html: canonical Token Junkie Labs handoff mailto missing", errors)


if __name__ == "__main__":
    unittest.main()
