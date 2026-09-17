from __future__ import annotations

from types import ModuleType
from typing import Any, Mapping
import unicodedata


_SENTINEL = "_human_reply_claim_guard_installed"
_UNSAFE_UNICODE_CATEGORIES = {"Cc", "Cf", "Cs", "Zl", "Zp"}


def _screen_form(core: ModuleType, text: str, where: str) -> str:
    # Caller-rendered text is a one-line commercial artifact boundary.  Reject
    # invisible controls/formatters and Unicode line/paragraph separators rather
    # than allowing them to split a dangerous assertion into regex-safe pieces.
    for char in text:
        if unicodedata.category(char) in _UNSAFE_UNICODE_CATEGORIES:
            raise core.WorkshareError(
                f"{where} contains unsafe Unicode control/format character"
            )

    # Compatibility normalization closes fullwidth and compatibility-glyph
    # variants.  Whitespace collapse closes non-ASCII spacing variants while the
    # original caller text remains unchanged for rendering after it is screened.
    normalized = unicodedata.normalize("NFKC", text)
    return " ".join(normalized.split())


def _guard_emitted_text(core: ModuleType, text: str, where: str) -> str:
    screened = _screen_form(core, text, where)
    for pattern in core._FORBIDDEN_SCOPE_ASSERTIONS:
        if pattern.search(screened):
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


def install_claim_guard(core: ModuleType) -> None:
    """Close unsupported-claim smuggling across every caller text emitted by the kit.

    The v1 engine guarded only ``scope.one_line`` and screened ASCII-shaped text.
    Package import installs this guard onto the canonical core module so normal
    package imports, ``package.core`` imports, and the CLI share one fail-closed
    commercial-text boundary while preserving the original workshare economics.
    """

    if getattr(core, _SENTINEL, False):
        return

    original_normalize = core.normalize_offer
    original_render = core.render_offer_markdown

    def guarded_normalize_offer(raw: Mapping[str, Any]) -> dict[str, Any]:
        normalized = original_normalize(raw)
        _guard_normalized(core, normalized)
        return normalized

    def guarded_render_offer_markdown(normalized: Mapping[str, Any]) -> str:
        # render_offer_markdown is public.  Revalidate instead of allowing callers
        # to bypass compile_offer by handing the renderer a forged normalized map.
        checked = guarded_normalize_offer(normalized)
        return original_render(checked)

    core.normalize_offer = guarded_normalize_offer
    core.render_offer_markdown = guarded_render_offer_markdown
    setattr(core, _SENTINEL, True)
