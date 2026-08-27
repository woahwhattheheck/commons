"""Paid-session lane for the existing TITAN Hands one-tool contract.

One MCP tool stays `titan_hands`. This is `target=pay`: live Commons Stripe
Payment Links already on HEAD, plus Checkout Sessions when STRIPE_SECRET_KEY
is set. The secret is read from the environment only. It is never invented
or written to the tree. A missing key is PAY_UNCONFIGURED with a measured
probe, same honesty as a missing AT-SPI bus. This lane does not mint a charge.

Cite: p/blink-titan-money-20260826-01.md
      p/plug-stop-prove-20260820-01.md
      p/coil-titan-hands-one-tool-20260826-01.md
      land/stripe-payment-links-20260826.md
Do not remint those receipts or the SKU files.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from host.titan_hands.lanes import PIXELS_NEVER, PIXELS_NOT_CAPTURED, LaneError, _SemanticLane, _node
from host.titan_hands_windows.protocol import PROTOCOL_VERSION, ProtocolError, failure


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STRIPE_API = "https://api.stripe.com/v1"
DEFAULT_SKU = "unlock"
SUCCESS_URL = "https://woahwhattheheck.github.io/commons/pay.html?session_id={CHECKOUT_SESSION_ID}"
CANCEL_URL = "https://woahwhattheheck.github.io/commons/pay.html"
SKU_FILES = {
    "tip": "land/sku-tip-20260826.md",
    "seat": "land/sku-seat-20260826.md",
    "unlock": "land/sku-unlock-20260826.md",
    "monthly-tip": "land/sku-monthly-tip-20260826.md",
    "boost": "land/sku-boost-20260826.md",
    "whitebox-hour": "land/sku-whitebox-hour-20260826.md",
    "muhlnickel-titan": "land/sku-muhlnickel-titan-20260826.md",
}
CHECKOUT_RE = re.compile(r"^https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9]+$")
CHECKOUT_SESSION_RE = re.compile(r"^cs_(?:test|live)_[A-Za-z0-9]+$")
PRICE_MONTH_RE = re.compile(r"month", re.I)


def _field(text: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(\S+)\s*$", text)
    return match.group(1) if match else ""


def load_live_skus(root: Path | None = None) -> dict[str, dict[str, str]]:
    """Read the already-landed LIVE Payment Link SKUs. Does not remint them."""

    base = Path(root or ROOT)
    rows: dict[str, dict[str, str]] = {}
    for slug, rel in SKU_FILES.items():
        path = base / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LaneError(
                "PAY_UNCONFIGURED",
                f"SKU file is not readable: {rel}",
                slug=slug,
                path=rel,
                error=f"{type(exc).__name__}: {exc}",
            ) from exc
        checkout = _field(text, "checkout")
        status = _field(text, "status")
        if status != "LIVE" or not CHECKOUT_RE.match(checkout):
            raise LaneError(
                "PAY_UNCONFIGURED",
                f"SKU {slug} is not a live Stripe Payment Link on this tree",
                slug=slug,
                status=status,
                checkout=checkout,
                path=rel,
            )
        price_line = ""
        for line in text.splitlines():
            if line.lower().startswith("price:"):
                price_line = line.split(":", 1)[1].strip()
                break
        rows[slug] = {
            "slug": slug,
            "checkout": checkout,
            "status": status,
            "price_id": _field(text, "price_id"),
            "product_id": _field(text, "product") or _field(text, "product_id"),
            "plink": _field(text, "plink"),
            "price": price_line,
            "path": rel,
            "mode": "subscription" if PRICE_MONTH_RE.search(price_line) else "payment",
        }
    return rows


def secret_key(environ: Mapping[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    return str(env.get("STRIPE_SECRET_KEY") or "").strip()


def measure_pay_transport(
    environ: Mapping[str, str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Measured probe. Absence of the secret is not a fake charge."""

    key = secret_key(environ)
    try:
        skus = load_live_skus(root)
        sku_error = ""
    except LaneError as exc:
        skus = {}
        sku_error = str(exc)
    links = [
        {"slug": slug, "checkout": row["checkout"], "price_id": row["price_id"], "mode": row["mode"]}
        for slug, row in skus.items()
    ]
    return {
        "env_name": "STRIPE_SECRET_KEY",
        "stripe_secret_key": bool(key),
        "stripe_api": STRIPE_API,
        "live_sku_count": len(skus),
        "live_payment_links": links,
        "default_sku": DEFAULT_SKU,
        "sku_error": sku_error,
        "checkout_sessions": "ready" if key else "unconfigured",
        "note": (
            "live buy.stripe.com / donate.stripe.com URLs already take money; "
            "Checkout Sessions need STRIPE_SECRET_KEY in the process environment"
        ),
    }


def stripe_request(
    method: str,
    path: str,
    secret: str,
    fields: Mapping[str, str] | None = None,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """POST/GET Stripe. The secret stays in the Authorization header, not on disk."""

    if not secret:
        raise LaneError(
            "PAY_UNCONFIGURED",
            "STRIPE_SECRET_KEY is empty; this process cannot create or verify a Checkout Session",
            **measure_pay_transport(),
        )
    body = urlencode(fields or {}).encode("utf-8") if fields is not None else None
    request = Request(
        STRIPE_API + path,
        data=body,
        method=method.upper(),
        headers={
            "Authorization": "Bearer " + secret,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    open_url = opener or urlopen
    try:
        with open_url(request, timeout=20) as handle:
            raw = handle.read()
            status = getattr(handle, "status", 200)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise LaneError(
            "PAY_PROVIDER_ERROR",
            f"Stripe HTTP {exc.code} on {method.upper()} {path}",
            http_status=exc.code,
            path=path,
            detail=detail,
        ) from exc
    except URLError as exc:
        raise LaneError(
            "PAY_PROVIDER_ERROR",
            f"Stripe transport failed: {exc.reason}",
            path=path,
            error=str(exc.reason),
        ) from exc
    except TimeoutError as exc:
        raise LaneError("PAY_PROVIDER_ERROR", "Stripe request timed out", path=path) from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise LaneError("PAY_PROVIDER_ERROR", "Stripe response was not JSON", path=path) from exc
    if not isinstance(payload, dict):
        raise LaneError("PAY_PROVIDER_ERROR", "Stripe response was not an object", path=path)
    payload.setdefault("_http_status", status)
    return payload


def mint_session_token(secret: str, checkout_session_id: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        checkout_session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"ths1.{checkout_session_id}.{digest[:24]}"


def parse_session_token(token: str) -> tuple[str, str]:
    parts = str(token or "").strip().split(".")
    if len(parts) != 3 or parts[0] != "ths1" or not parts[1] or not parts[2]:
        raise LaneError("PAY_UNPAID", "paid_session is not a titan_hands checkout handle")
    return parts[1], parts[2]


def session_token_matches(secret: str, token: str) -> str:
    session_id, suffix = parse_session_token(token)
    expected = mint_session_token(secret, session_id)
    if not hmac.compare_digest(expected, token):
        raise LaneError("PAY_UNPAID", "paid_session does not match this STRIPE_SECRET_KEY")
    return session_id


def secret_livemode(secret: str) -> bool | None:
    """Infer the Stripe environment without exposing any secret bytes."""

    if secret.startswith(("sk_live_", "rk_live_")):
        return True
    if secret.startswith(("sk_test_", "rk_test_")):
        return False
    return None


def session_binding(retrieved: Mapping[str, Any]) -> tuple[bool, str]:
    """Require a Checkout Session minted by this lane, not any paid account session."""

    metadata = retrieved.get("metadata")
    if not isinstance(metadata, Mapping):
        return False, ""
    sku = str(metadata.get("commons_sku") or "").strip().lower()
    bound = (
        str(metadata.get("titan_hands") or "") == "paid_session"
        and str(retrieved.get("client_reference_id") or "") == "titan-hands-paid-session"
        and sku in SKU_FILES
    )
    return bound, sku


class PayServer(_SemanticLane):
    """Stripe Payment Link + Checkout Session on handle({op})."""

    platform = "pay"
    observation = "pay-semantic-delta"
    pixels = PIXELS_NEVER
    actions = ("link", "checkout", "verify")

    def __init__(
        self,
        root: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
        stripe: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        super().__init__()
        self.root = Path(root or ROOT)
        self.environ = dict(environ) if environ is not None else None
        self.stripe = stripe or stripe_request

    def _env(self) -> Mapping[str, str]:
        return self.environ if self.environ is not None else os.environ

    def _secret(self) -> str:
        return secret_key(self._env())

    def _skus(self) -> dict[str, dict[str, str]]:
        return load_live_skus(self.root)

    def _sku(self, request: Mapping[str, Any], action: Mapping[str, Any] | None = None) -> dict[str, str]:
        raw = ""
        if action:
            raw = str(action.get("sku") or action.get("id") or "")
        if not raw:
            raw = str(request.get("sku") or self._env().get("TITAN_HANDS_PAY_SKU") or DEFAULT_SKU)
        slug = raw.strip().lower()
        skus = self._skus()
        if slug not in skus:
            raise ProtocolError(f"unknown Commons SKU: {slug}")
        return skus[slug]

    def _probe(self) -> dict[str, Any]:
        return measure_pay_transport(self._env(), self.root)

    def _capabilities(self) -> dict[str, Any]:
        probe = self._probe()
        result = super()._capabilities()
        result.update(
            {
                "charge_path": "stripe",
                "stripe_secret_key": probe["stripe_secret_key"],
                "default_sku": DEFAULT_SKU,
                "live_sku_count": probe["live_sku_count"],
                "checkout_sessions": probe["checkout_sessions"],
                "model_facing_tools": 1,
            }
        )
        return result

    def _snapshot(self, request: Mapping[str, Any]) -> dict[str, Any]:
        del request
        probe = self._probe()
        nodes = [
            _node(
                "pay:catalog",
                "Catalog",
                "Commons live Stripe Payment Links",
                actions=["link", "checkout"],
                live_sku_count=probe["live_sku_count"],
            ),
            _node(
                "pay:session",
                "Receipt",
                "paid checkout session",
                parent="pay:catalog",
                actions=["verify", "checkout"],
            ),
        ]
        for slug, row in self._skus().items():
            nodes.append(
                _node(
                    f"pay:sku:{slug}",
                    "Link",
                    slug,
                    parent="pay:catalog",
                    actions=["link", "checkout"],
                    checkout=row["checkout"],
                    price_id=row["price_id"],
                    mode=row["mode"],
                    status=row["status"],
                )
            )
        return {
            "ok": True,
            "nodes": nodes,
            "kind": "semantic_snapshot",
            "platform": "pay",
            "pixels": PIXELS_NOT_CAPTURED,
            "probe": probe,
        }

    def _act(self, action: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        action_type = str(action.get("type") or "").strip().lower()
        if action_type == "link":
            sku = self._sku(request, action)
            return {
                "ok": True,
                "protocol": PROTOCOL_VERSION,
                "kind": "action_outcome",
                "platform": "pay",
                "action": "link",
                "sku": sku["slug"],
                "checkout_url": sku["checkout"],
                "price_id": sku["price_id"],
                "mode": sku["mode"],
                "provider": "stripe",
                "charge": "payment_link",
                "note": "This URL is the already-landed live Payment Link. It takes money.",
            }
        if action_type == "checkout":
            return self._checkout(request, action)
        if action_type in {"verify", "session"}:
            return self._verify(request, action)
        return failure("UNKNOWN_OPERATION", f"pay lane has no handler for {action_type or '<empty>'}")

    def _checkout(self, request: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
        sku = self._sku(request, action)
        secret = self._secret()
        if not secret:
            return failure(
                "PAY_UNCONFIGURED",
                "STRIPE_SECRET_KEY is empty; Checkout Session was not created and no charge was minted",
                **self._probe(),
                sku=sku["slug"],
                payment_link=sku["checkout"],
            )
        if not sku["price_id"]:
            raise LaneError("PAY_UNCONFIGURED", f"SKU {sku['slug']} has no price_id on this tree", **sku)
        created = self.stripe(
            "POST",
            "/checkout/sessions",
            secret,
            {
                "mode": sku["mode"],
                "success_url": str(action.get("success_url") or request.get("success_url") or SUCCESS_URL),
                "cancel_url": str(action.get("cancel_url") or request.get("cancel_url") or CANCEL_URL),
                "client_reference_id": "titan-hands-paid-session",
                "line_items[0][price]": sku["price_id"],
                "line_items[0][quantity]": "1",
                "metadata[titan_hands]": "paid_session",
                "metadata[commons_sku]": sku["slug"],
            },
        )
        session_id = str(created.get("id") or "")
        url = str(created.get("url") or "")
        if not session_id or not url:
            raise LaneError(
                "PAY_PROVIDER_ERROR",
                "Stripe Checkout Session response missed id or url",
                keys=sorted(created),
            )
        return {
            "ok": True,
            "protocol": PROTOCOL_VERSION,
            "kind": "action_outcome",
            "platform": "pay",
            "action": "checkout",
            "sku": sku["slug"],
            "checkout_url": url,
            "checkout_session_id": session_id,
            "payment_status": str(created.get("payment_status") or "unpaid"),
            "livemode": bool(created.get("livemode")),
            "provider": "stripe",
            "charge": "checkout_session",
            "price_id": sku["price_id"],
            "mode": sku["mode"],
        }

    def _verify(self, request: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
        secret = self._secret()
        if not secret:
            return failure(
                "PAY_UNCONFIGURED",
                "STRIPE_SECRET_KEY is empty; this process cannot verify a Checkout Session",
                **self._probe(),
            )
        token = str(
            action.get("paid_session")
            or action.get("session")
            or request.get("paid_session")
            or request.get("session")
            or ""
        ).strip()
        session_id = str(
            action.get("checkout_session_id")
            or action.get("id")
            or request.get("checkout_session_id")
            or ""
        ).strip()
        if token:
            session_id = session_token_matches(secret, token)
        if not session_id:
            raise ProtocolError("verify needs checkout_session_id or paid_session")
        if not CHECKOUT_SESSION_RE.fullmatch(session_id):
            return failure(
                "PAY_UNBOUND",
                "checkout_session_id is not a Stripe Checkout Session id",
                checkout_session_id=session_id,
            )
        retrieved = self.stripe("GET", f"/checkout/sessions/{session_id}", secret, None)
        payment_status = str(retrieved.get("payment_status") or "")
        livemode = bool(retrieved.get("livemode"))
        bound, sku = session_binding(retrieved)
        if not bound:
            return failure(
                "PAY_UNBOUND",
                "Stripe Checkout Session is not bound to the titan_hands paid-session contract",
                checkout_session_id=session_id,
                payment_status=payment_status,
                livemode=livemode,
            )
        expected_livemode = secret_livemode(secret)
        if expected_livemode is not None and livemode != expected_livemode:
            return failure(
                "PAY_UNBOUND",
                "Stripe Checkout Session livemode does not match this process key",
                checkout_session_id=session_id,
                livemode=livemode,
            )
        provider_paid = payment_status == "paid"
        paid = provider_paid and livemode
        result = {
            "ok": paid,
            "protocol": PROTOCOL_VERSION,
            "kind": "action_outcome" if paid else "failure",
            "platform": "pay",
            "action": "verify",
            "checkout_session_id": session_id,
            "payment_status": payment_status,
            "livemode": livemode,
            "provider": "stripe",
            "sku": sku,
            "provider_paid": provider_paid,
            "paid": paid,
        }
        if provider_paid and not livemode:
            result["failure_reason"] = "PAY_TESTMODE"
            result["message"] = "Stripe confirms payment only in test mode; no paid-session handle was minted"
            result["evidence"] = {
                "checkout_session_id": session_id,
                "payment_status": payment_status,
                "livemode": False,
                "sku": sku,
            }
            return result
        if paid:
            result["paid_session"] = mint_session_token(secret, session_id)
            return result
        result["failure_reason"] = "PAY_UNPAID"
        result["message"] = f"Stripe Checkout Session {session_id} payment_status={payment_status or 'empty'}"
        result["evidence"] = {"checkout_session_id": session_id, "payment_status": payment_status}
        return result


def require_paid_session(
    request: Mapping[str, Any],
    *,
    pay: PayServer | None = None,
    environ: Mapping[str, str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Verify a paid checkout handle when the secret is present.

    Local windows/android/linux/files/git/slack/board/shell/browser stay open.
    This is a charge measurement for remote/wireless bind, not a speaker lock.
    """

    server = pay or PayServer(root=root, environ=environ)
    secret = server._secret()
    if not secret:
        return failure(
            "PAY_UNCONFIGURED",
            "STRIPE_SECRET_KEY is empty; wireless bind cannot verify a paid checkout session",
            **server._probe(),
        )
    token = str(request.get("paid_session") or request.get("session") or "")
    action = request.get("action") if isinstance(request.get("action"), Mapping) else {}
    if not token and action:
        token = str(action.get("paid_session") or action.get("session") or "")
    session_id = str(request.get("checkout_session_id") or action.get("checkout_session_id") or "")
    return server.handle(
        {
            "op": "act",
            "action": {
                "type": "verify",
                "paid_session": token,
                "checkout_session_id": session_id,
            },
            "observe_after": False,
        }
    )
