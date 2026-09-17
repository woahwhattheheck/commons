from __future__ import annotations

import hashlib
import html
import importlib.abc
import importlib.machinery
import re
import sys
from types import ModuleType
from typing import Any, Mapping
import unicodedata


_SENTINEL = "_human_reply_claim_guard_installed"
_GUARD_VERSION = "human-reply-claim-guard/v5"
_RELOAD_FINDER_SENTINEL = "_human_reply_claim_guard_reload_finder"
_CORE_NAME = "revenue.human_reply_workshare_kit.core"
_UNSAFE_UNICODE_CATEGORIES = {"Cc", "Cf", "Cs", "Zl", "Zp"}
_HTML_MARKUP = re.compile(r"<(?:/?[A-Za-z][^<>]*|![^<>]*|\?[^<>]*)>")
# Markdown destinations can be semantically invisible in rendered text.  For
# example, ``Buyer [](https://example.invalid) accepted`` screens as source text
# containing URL tokens but renders visibly as ``Buyer accepted``.  Reject the
# destination-bearing syntax itself instead of attempting to predict every
# downstream Markdown renderer.  The boundary is deliberately conservative:
# images, inline links, full/collapsed reference links, and reference definitions
# are not needed in these one-line caller-authored commercial fields.
_MARKDOWN_DESTINATION_SYNTAX = re.compile(
    r"(?:!\[|\]\s*(?:\(|\[)|^\s*\[[^\]\r\n]+\]\s*:)", re.MULTILINE
)

# Run these over a punctuation-folded semantic skeleton. The original v1
# patterns remain authoritative too; this closes buyer-facing Markdown and
# punctuation splits without rejecting nonassertive phrases such as
# "acceptance evidence".
_FORBIDDEN_RENDERED_ASSERTIONS = (
    re.compile(r"\bbuyer\s+(?:has\s+)?accepted\b", re.I),
    re.compile(r"\baccepted\s+by\s+(?:the\s+)?buyer\b", re.I),
    re.compile(r"\b(?:we|tjlabs)\s+(?:have\s+|has\s+)?(?:been\s+)?awarded\b", re.I),
    re.compile(r"\b(?:work|contract|engagement)\s+(?:(?:was|is)\s+|has\s+been\s+)?awarded\b", re.I),
    re.compile(r"\baward\s+(?:is\s+)?secured\b", re.I),
    re.compile(r"\b(?:already\s+|were\s+|was\s+)?paid\b", re.I),
    re.compile(r"\bpayment\s+(?:(?:was|is)\s+|has\s+been\s+)?(?:received|settled)\b", re.I),
    re.compile(r"\binvoice\s+(?:(?:was|is)\s+|has\s+been\s+)?(?:issued|sent)\b", re.I),
    re.compile(r"\b(?:signed\s+contract|contract\s+(?:(?:was|is)\s+|has\s+been\s+)?signed)\b", re.I),
    re.compile(r"\bbooked\s+revenue\b", re.I),
    re.compile(r"\brecognized\s+revenue\b", re.I),
    re.compile(r"\b(?:existing|current)\s+customer\b", re.I),
    re.compile(r"\bcustomer\s+relationship\s+(?:(?:is|was)\s+)?(?:established|confirmed|active)\b", re.I),
    re.compile(r"\bguaranteed\s+(?:savings|outcome|roi|acceptance|award)\b", re.I),
)


def _screen_form(core: ModuleType, text: str, where: str) -> str:
    # Caller-rendered text is a one-line commercial artifact boundary. Reject
    # invisible controls/formatters and Unicode line/paragraph separators rather
    # than allowing them to split a dangerous assertion into regex-safe pieces.
    for char in text:
        if unicodedata.category(char) in _UNSAFE_UNICODE_CATEGORIES:
            raise core.WorkshareError(
                f"{where} contains unsafe Unicode control/format character"
            )

    # Compatibility normalization closes fullwidth and compatibility-glyph
    # variants. Raw HTML is not admitted at this boundary: Markdown renderers can
    # erase inline tag names, and HTML entity decoding can turn a source string
    # that looks harmless to a regex into a stronger visible commercial claim.
    # Reject both classes before any Markdown emission rather than trying to
    # predict a downstream renderer's HTML policy. html.unescape implements the
    # HTML5 named/numeric entity table, including legacy semicolonless forms.
    normalized = unicodedata.normalize("NFKC", text)
    if _HTML_MARKUP.search(normalized):
        raise core.WorkshareError(f"{where} contains unsupported HTML markup")
    if html.unescape(normalized) != normalized:
        raise core.WorkshareError(f"{where} contains unsupported HTML entity syntax")
    if _MARKDOWN_DESTINATION_SYNTAX.search(normalized):
        raise core.WorkshareError(
            f"{where} contains unsupported Markdown link/image/reference syntax"
        )

    # Whitespace collapse closes non-ASCII spacing variants while the original
    # caller text remains unchanged for rendering after it is screened.
    return " ".join(normalized.split())


def _commercial_skeleton(text: str) -> str:
    folded = text.casefold()
    return " ".join("".join(char if char.isalnum() else " " for char in folded).split())


def _guard_emitted_text(core: ModuleType, text: str, where: str) -> str:
    screened = _screen_form(core, text, where)
    skeleton = _commercial_skeleton(screened)
    patterns = tuple(core._FORBIDDEN_SCOPE_ASSERTIONS) + _FORBIDDEN_RENDERED_ASSERTIONS
    for pattern in patterns:
        candidate = skeleton if pattern in _FORBIDDEN_RENDERED_ASSERTIONS else screened
        if pattern.search(candidate):
            raise core.WorkshareError(
                f"{where} contains unsupported commercial/outcome assertion"
            )
    return text


def _guard_normalized(core: ModuleType, normalized: Mapping[str, Any]) -> None:
    _guard_emitted_text(core, str(normalized["counterparty_label"]), "counterparty_label")
    _guard_emitted_text(core, str(normalized["opportunity_label"]), "opportunity_label")
    scope = normalized["scope"]
    _guard_emitted_text(core, str(scope["one_line"]), "scope.one_line")
    for index, item in enumerate(scope["input_bounds"]):
        _guard_emitted_text(core, str(item), f"scope.input_bounds[{index}]")


def _mark_guarded(function: Any) -> Any:
    setattr(function, _SENTINEL, _GUARD_VERSION)
    return function


def _is_current_guard(function: Any) -> bool:
    return getattr(function, _SENTINEL, None) == _GUARD_VERSION


class _ReloadSealLoader(importlib.abc.Loader):
    """Make ordinary ``importlib.reload(core)`` a safe in-process no-op.

    This authority module is deliberately reload-sealed: source-generation
    changes take effect in a fresh interpreter, while a reload cannot recreate
    the pre-guard function graph in the existing module object.
    """

    def create_module(self, spec):  # pragma: no cover - reload reuses the module
        return None

    def exec_module(self, module: ModuleType) -> None:
        install_claim_guard(module, install_reload_seal=False)


class _ReloadSealFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: Any, target: ModuleType | None = None):
        if fullname != _CORE_NAME or target is None:
            return None
        previous = getattr(target, "__spec__", None)
        origin = getattr(previous, "origin", None)
        return importlib.machinery.ModuleSpec(fullname, _ReloadSealLoader(), origin=origin)


def _install_reload_seal() -> None:
    for finder in sys.meta_path:
        if getattr(finder, _RELOAD_FINDER_SENTINEL, False):
            return
    finder = _ReloadSealFinder()
    setattr(finder, _RELOAD_FINDER_SENTINEL, True)
    sys.meta_path.insert(0, finder)


def install_claim_guard(core: ModuleType, *, install_reload_seal: bool = True) -> None:
    """Install the fail-closed commercial-truth and receipt-integrity boundary.

    Every caller-controlled rendered field re-enters one screen, public rendering
    revalidates the complete normalized offer, and public receipt rendering binds
    current normalized state + regenerated Markdown + canonical SHA-256. The
    canonical ``core`` module is also reload-sealed so ordinary ``importlib.reload``
    cannot resurrect its pre-guard authority graph.
    """

    guarded_names = ("normalize_offer", "render_offer_markdown", "render_receipt_json")
    if all(_is_current_guard(getattr(core, name, None)) for name in guarded_names):
        setattr(core, _SENTINEL, _GUARD_VERSION)
        if install_reload_seal:
            _install_reload_seal()
        return

    original_normalize = core.normalize_offer
    original_render = core.render_offer_markdown
    original_receipt = core.render_receipt_json

    @_mark_guarded
    def guarded_normalize_offer(raw: Mapping[str, Any]) -> dict[str, Any]:
        normalized = original_normalize(raw)
        _guard_normalized(core, normalized)
        return normalized

    @_mark_guarded
    def guarded_render_offer_markdown(normalized: Mapping[str, Any]) -> str:
        # Public rendering is an authority-bearing entry point. Revalidate the
        # complete object instead of accepting a caller-forged normalized map.
        checked = guarded_normalize_offer(normalized)
        return original_render(checked)

    @_mark_guarded
    def guarded_render_receipt_json(compiled: Any) -> str:
        if not isinstance(compiled, core.CompiledOffer):
            raise core.WorkshareError("compiled offer must be CompiledOffer")
        checked = guarded_normalize_offer(compiled.normalized)
        expected_markdown = original_render(checked)
        expected_sha256 = hashlib.sha256(
            core.canonical_json(checked).encode("utf-8")
        ).hexdigest()
        if compiled.markdown != expected_markdown:
            raise core.WorkshareError("compiled markdown does not match normalized offer")
        if compiled.receipt_sha256 != expected_sha256:
            raise core.WorkshareError("compiled receipt hash does not match normalized offer")
        canonical = core.CompiledOffer(
            normalized=checked,
            markdown=expected_markdown,
            receipt_sha256=expected_sha256,
        )
        return original_receipt(canonical)

    core.normalize_offer = guarded_normalize_offer
    core.render_offer_markdown = guarded_render_offer_markdown
    core.render_receipt_json = guarded_render_receipt_json
    setattr(core, _SENTINEL, _GUARD_VERSION)
    if install_reload_seal:
        _install_reload_seal()
