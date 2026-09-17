"""Closed provider inventory and repository bypass scanner.

This registry is deliberately redundant with the typed provider boundary: CI checks
that every declared adapter and boundary exists, then rejects repository code that
reaches lower one-shot primitives or provider mutation surfaces outside the guarded
chain.  Host connector identities are also enumerated so runtime/operator policy can
bind the same closed set; repository CI cannot intercept an out-of-process connector
call that never enters repository code.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Adapter:
    provider: str
    module_path: str
    callable_name: str
    boundary_module_path: str
    boundary_class_name: str
    transport_method: str
    host_mutation_identities: tuple[str, ...]


ADAPTERS = (
    Adapter(
        "gmail",
        "revenue/organization_outbound_chain/adapters.py",
        "gmail_initial_outreach",
        "revenue/organization_outbound_chain/provider_boundary.py",
        "GmailBoundary",
        "gmail_send_message",
        (
            "mcp__Gmail__send_email",
            "mcp__Gmail__send_draft",
            "mcp__Gmail__forward_emails",
        ),
    ),
    Adapter(
        "slack_dm",
        "revenue/organization_outbound_chain/adapters.py",
        "slack_dm_initial_outreach",
        "revenue/organization_outbound_chain/provider_boundary.py",
        "SlackDmBoundary",
        "slack_send_dm",
        (
            "mcp__Slack__slack_send_message",
            "mcp__Slack__slack_schedule_message",
        ),
    ),
    Adapter(
        "discord",
        "revenue/organization_outbound_chain/adapters.py",
        "discord_initial_outreach",
        "revenue/organization_outbound_chain/provider_boundary.py",
        "DiscordBoundary",
        "discord_send_message",
        (
            "discord.Webhook.send",
            "discord.webhook.execute",
        ),
    ),
    Adapter(
        "webhook_mail",
        "revenue/organization_outbound_chain/adapters.py",
        "webhook_mail_initial_outreach",
        "revenue/organization_outbound_chain/provider_boundary.py",
        "WebhookMailBoundary",
        "webhook_mail_send",
        ("http.webhook_mail.post",),
    ),
)

_EXPECTED_PROVIDERS = ("gmail", "slack_dm", "discord", "webhook_mail")
_PROVIDER_METHODS = frozenset(item.transport_method for item in ADAPTERS)
_HOST_MUTATION_IDENTITIES = frozenset(
    identity for item in ADAPTERS for identity in item.host_mutation_identities
)

# Concrete SDK/API spellings that constitute provider-send surfaces if they appear
# in repository code outside the registered boundary implementation.
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
    *tuple(sorted(_HOST_MUTATION_IDENTITIES)),
)

_LOW_LEVEL_TARGETS = {
    "revenue.initial_outreach_slot.execute_initial_outreach": "direct-initial-outreach",
    "revenue.initial_outreach_slot.slot.execute_initial_outreach": "direct-initial-outreach",
    "revenue.outbound_send_consumer.consume_once": "direct-terminal-consumer",
    "revenue.outbound_send_consumer.consume.consume_once": "direct-terminal-consumer",
}
_LOW_LEVEL_MODULES = {
    "revenue.initial_outreach_slot",
    "revenue.initial_outreach_slot.slot",
    "revenue.outbound_send_consumer",
    "revenue.outbound_send_consumer.consume",
}
_LOW_LEVEL_PRIMITIVES = {
    "revenue/initial_outreach_slot/slot.py",
    "revenue/outbound_send_consumer/consume.py",
}
_CHAIN_FILES = {
    "revenue/organization_outbound_chain/chain.py",
    "revenue/organization_outbound_chain/adapters.py",
    "revenue/organization_outbound_chain/provider_boundary.py",
    "revenue/organization_outbound_chain/registry.py",
}
_PROVIDER_METHOD_ALLOWED = {
    "revenue/organization_outbound_chain/provider_boundary.py",
}
_MARKER_ALLOWED = {
    "revenue/organization_outbound_chain/provider_boundary.py",
    "revenue/organization_outbound_chain/registry.py",
}
_CODE_SUFFIXES = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".rb", ".go", ".rs", ".java", ".kt", ".kts", ".sh", ".ps1",
})


def _is_test(path: str) -> bool:
    name = Path(path).name
    return (
        name.startswith("test_")
        or "/tests/" in f"/{path}"
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".test.ts")
    )


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return None if head is None else f"{head}.{node.attr}"
    return None


def _target_label(dotted: str | None) -> str | None:
    if not dotted:
        return None
    if dotted in _LOW_LEVEL_TARGETS:
        return _LOW_LEVEL_TARGETS[dotted]
    for target, label in _LOW_LEVEL_TARGETS.items():
        if dotted.endswith("." + target):
            return label
    return None


def _python_call_violations(tree: ast.AST) -> set[str]:
    """Resolve direct imports, aliases and simple rebinding of guarded callsites."""
    callable_aliases: dict[str, str] = {}
    module_aliases: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                module_aliases[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                local = alias.asname or alias.name
                target = f"{module}.{alias.name}" if module else alias.name
                label = _target_label(target)
                if label:
                    callable_aliases[local] = label
                if target in _LOW_LEVEL_MODULES:
                    module_aliases[local] = target

    # Resolve one or more simple alias assignments, including:
    # f = consume_once; f = module.consume_once.
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            names: list[str] = []
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node.target, ast.Name):
                names = [node.target.id]
            label = None
            if isinstance(value, ast.Name):
                label = callable_aliases.get(value.id)
            else:
                dotted = _dotted(value) if value is not None else None
                if dotted:
                    root, _, rest = dotted.partition(".")
                    if root in module_aliases:
                        dotted = module_aliases[root] + ("." + rest if rest else "")
                    label = _target_label(dotted)
            if label:
                for name in names:
                    if callable_aliases.get(name) != label:
                        callable_aliases[name] = label
                        changed = True

    violations: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name):
            label = callable_aliases.get(fn.id)
            if label:
                violations.add(label)
        else:
            dotted = _dotted(fn)
            if dotted:
                root, _, rest = dotted.partition(".")
                if root in module_aliases:
                    dotted = module_aliases[root] + ("." + rest if rest else "")
                label = _target_label(dotted)
                if label:
                    violations.add(label)
            if isinstance(fn, ast.Attribute) and fn.attr in _PROVIDER_METHODS:
                violations.add(f"provider-transport-method:{fn.attr}")

        # Literal getattr(module, "consume_once") / getattr(..., provider_method)
        if (
            isinstance(fn, ast.Name)
            and fn.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            attr = node.args[1].value
            if attr == "execute_initial_outreach":
                violations.add("dynamic-initial-outreach")
            elif attr == "consume_once":
                violations.add("dynamic-terminal-consumer")
            elif attr in _PROVIDER_METHODS:
                violations.add(f"dynamic-provider-transport-method:{attr}")
    return violations


def _top_level_defs(tree: ast.AST) -> tuple[set[str], set[str]]:
    functions: set[str] = set()
    classes: set[str] = set()
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
    return functions, classes


def validate_registry(repository_root: str | Path) -> list[str]:
    """Prove the provider manifest is closed and its named code surfaces exist."""
    root = Path(repository_root)
    violations: list[str] = []
    providers = tuple(item.provider for item in ADAPTERS)
    if providers != _EXPECTED_PROVIDERS:
        violations.append("registry:provider-set-not-exact")
    if len(set(providers)) != len(providers):
        violations.append("registry:duplicate-provider")
    if len(_PROVIDER_METHODS) != len(ADAPTERS):
        violations.append("registry:duplicate-transport-method")

    for item in ADAPTERS:
        if not item.host_mutation_identities:
            violations.append(f"registry:{item.provider}:host-mutation-identities-empty")
        adapter_path = root / item.module_path
        boundary_path = root / item.boundary_module_path
        try:
            adapter_tree = ast.parse(adapter_path.read_text(encoding="utf-8"), filename=item.module_path)
        except (OSError, UnicodeError, SyntaxError) as exc:
            violations.append(f"registry:{item.provider}:adapter-unreadable:{type(exc).__name__}")
            continue
        try:
            boundary_tree = ast.parse(boundary_path.read_text(encoding="utf-8"), filename=item.boundary_module_path)
        except (OSError, UnicodeError, SyntaxError) as exc:
            violations.append(f"registry:{item.provider}:boundary-unreadable:{type(exc).__name__}")
            continue
        adapter_functions, _ = _top_level_defs(adapter_tree)
        _, boundary_classes = _top_level_defs(boundary_tree)
        boundary_methods = {
            node.name
            for node in ast.walk(boundary_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if item.callable_name not in adapter_functions:
            violations.append(f"registry:{item.provider}:adapter-callable-missing")
        if item.boundary_class_name not in boundary_classes:
            violations.append(f"registry:{item.provider}:boundary-class-missing")
        if item.transport_method not in boundary_methods:
            violations.append(f"registry:{item.provider}:transport-method-missing")

    return sorted(set(violations))


def _iter_code_files(root: Path) -> Iterable[Path]:
    for file in root.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in _CODE_SUFFIXES:
            continue
        parts = set(file.parts)
        if ".git" in parts or "node_modules" in parts or "__pycache__" in parts:
            continue
        yield file


def find_bypasses(
    repository_root: str | Path,
    *,
    validate_manifest: bool = True,
) -> list[str]:
    """Return code paths that bypass the mandatory provider-bound composition.

    Python analysis resolves imports, aliases and simple callable rebinding instead
    of matching only literal function names.  All supported code extensions are also
    scanned for known concrete provider/host mutation identities.  Tests and the
    primitive implementations are not live callers.
    """
    root = Path(repository_root)
    violations: list[str] = []
    if validate_manifest:
        violations.extend(validate_registry(root))

    for file in _iter_code_files(root):
        rel = file.relative_to(root).as_posix()
        if _is_test(rel) or rel in _LOW_LEVEL_PRIMITIVES:
            continue
        try:
            source = file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            violations.append(f"{rel}:unscannable:{type(exc).__name__}")
            continue

        if file.suffix.lower() == ".py":
            try:
                tree = ast.parse(source, filename=rel)
            except SyntaxError as exc:
                violations.append(f"{rel}:unscannable:{type(exc).__name__}")
                continue
            if rel not in _CHAIN_FILES:
                for label in _python_call_violations(tree):
                    violations.append(f"{rel}:{label}")
            elif rel not in _PROVIDER_METHOD_ALLOWED:
                for label in _python_call_violations(tree):
                    if label.startswith("provider-transport-method:") or label.startswith("dynamic-provider-transport-method:"):
                        violations.append(f"{rel}:{label}")

        if rel not in _MARKER_ALLOWED:
            for marker in PROVIDER_MARKERS:
                if marker in source:
                    violations.append(f"{rel}:provider-marker:{marker}")

    return sorted(set(violations))


def registered_provider_names() -> tuple[str, ...]:
    return tuple(item.provider for item in ADAPTERS)


def registered_host_mutation_identities() -> tuple[str, ...]:
    return tuple(sorted(_HOST_MUTATION_IDENTITIES))
