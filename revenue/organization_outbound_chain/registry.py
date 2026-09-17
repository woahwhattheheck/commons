"""Fail-closed repository inventory for outbound provider mutation surfaces."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Adapter:
    provider: str
    module_path: str
    callable_name: str
    external_mutation_callsite: str


ADAPTERS = (
    Adapter("gmail", "revenue/organization_outbound_chain/adapters.py", "gmail_initial_outreach", "provider_callback inside chain.consume_once"),
    Adapter("slack_dm", "revenue/organization_outbound_chain/adapters.py", "slack_dm_initial_outreach", "provider_callback inside chain.consume_once"),
    Adapter("discord", "revenue/organization_outbound_chain/adapters.py", "discord_initial_outreach", "provider_callback inside chain.consume_once"),
    Adapter("webhook_mail", "revenue/organization_outbound_chain/adapters.py", "webhook_mail_initial_outreach", "provider_callback inside chain.consume_once"),
)

# Concrete direct-provider APIs. Keep this list intentionally narrow and high-signal;
# future adapters must extend both the registry and marker set in the same change.
PROVIDER_MARKERS = (
    "smtplib.SMTP",
    ".sendmail(",
    "users().messages().send(",
    "chat_postMessage(",
    "slack_send_message(",
    "discord.Webhook",
    "hooks.slack.com/services/",
    "api.sendgrid.com/",
    "api.mailgun.net/",
)

_LOW_LEVEL_PRIMITIVES = {
    "revenue/initial_outreach_slot/slot.py",
    "revenue/outbound_send_consumer/consume.py",
}
_CHAIN_FILES = {
    "revenue/organization_outbound_chain/chain.py",
    "revenue/organization_outbound_chain/adapters.py",
    "revenue/organization_outbound_chain/registry.py",
}


def _is_test(path: str) -> bool:
    name = Path(path).name
    return name.startswith("test_") or "/tests/" in f"/{path}" or name.endswith("_test.py")


def _calls(tree: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == name:
            return True
        if isinstance(fn, ast.Attribute) and fn.attr == name:
            return True
    return False


def find_bypasses(repository_root: str | Path) -> list[str]:
    """Return source paths that can bypass the mandatory composition layer.

    The scan fails closed on direct lower-primitive invocation outside this package
    and on known provider mutation markers outside registered adapters. Test code and
    the low-level primitives themselves are excluded because they prove the seam; they
    are not live adapter callers.
    """
    root = Path(repository_root)
    violations: list[str] = []
    for file in root.rglob("*.py"):
        rel = file.relative_to(root).as_posix()
        if _is_test(rel) or rel in _LOW_LEVEL_PRIMITIVES or rel in _CHAIN_FILES:
            continue
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel)
        except (OSError, UnicodeError, SyntaxError) as exc:
            violations.append(f"{rel}:unscannable:{type(exc).__name__}")
            continue
        if _calls(tree, "execute_initial_outreach"):
            violations.append(f"{rel}:direct-initial-outreach")
        if _calls(tree, "consume_once"):
            violations.append(f"{rel}:direct-terminal-consumer")
        for marker in PROVIDER_MARKERS:
            if marker in source:
                violations.append(f"{rel}:provider-marker:{marker}")
    return sorted(set(violations))


def registered_provider_names() -> tuple[str, ...]:
    return tuple(item.provider for item in ADAPTERS)
