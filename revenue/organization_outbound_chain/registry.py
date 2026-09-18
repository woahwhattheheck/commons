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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .provider_boundary import (
    ProviderBoundaryError,
    registered_boundary_generation,
    registered_boundary_types,
)


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


def _python_call_violations(
    tree: ast.AST,
    *,
    _provider_methods: frozenset[str] = _PROVIDER_METHODS,
) -> set[str]:
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
            if isinstance(fn, ast.Attribute) and fn.attr in _provider_methods:
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
            elif attr in _provider_methods:
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


def validate_registry(
    repository_root: str | Path,
    *,
    _trusted_adapters: tuple[Adapter, ...] = ADAPTERS,
    _expected_providers: tuple[str, ...] = _EXPECTED_PROVIDERS,
    _provider_methods: frozenset[str] = _PROVIDER_METHODS,
) -> list[str]:
    """Prove the first-load provider manifest and runtime generation are closed.

    Public ADAPTERS and provider-boundary ClassVars are compatibility views only.
    Ordinary post-import rebinding cannot redefine the generation used here; any
    visible drift is reported as a failure instead of becoming new authority.
    """
    root = Path(repository_root)
    violations: list[str] = []
    if ADAPTERS != _trusted_adapters:
        violations.append("registry:public-manifest-drift")

    providers = tuple(item.provider for item in _trusted_adapters)
    if providers != _expected_providers:
        violations.append("registry:provider-set-not-exact")
    if len(set(providers)) != len(providers):
        violations.append("registry:duplicate-provider")
    if len(_provider_methods) != len(_trusted_adapters):
        violations.append("registry:duplicate-transport-method")

    try:
        runtime_generation = registered_boundary_generation()
        runtime_types = registered_boundary_types()
    except ProviderBoundaryError:
        violations.append("registry:runtime-boundary-metadata-drift")
        return sorted(set(violations))

    runtime_by_name = {
        boundary_type.__name__: (
            boundary_type,
            provider,
            transport_method,
            tuple(host_identities),
        )
        for boundary_type, provider, transport_method, host_identities
        in runtime_generation
    }
    if len(runtime_by_name) != len(runtime_generation):
        violations.append("registry:duplicate-runtime-boundary-type")
    if tuple(entry[0] for entry in runtime_generation) != runtime_types:
        violations.append("registry:runtime-boundary-type-view-mismatch")
    if set(runtime_by_name) != {
        item.boundary_class_name for item in _trusted_adapters
    }:
        violations.append("registry:runtime-boundary-set-not-exact")

    for item in _trusted_adapters:
        runtime_entry = runtime_by_name.get(item.boundary_class_name)
        if runtime_entry is None:
            violations.append(f"registry:{item.provider}:runtime-boundary-missing")
        else:
            _boundary_type, provider, transport_method, host_identities = runtime_entry
            if provider != item.provider:
                violations.append(f"registry:{item.provider}:runtime-provider-mismatch")
            if transport_method != item.transport_method:
                violations.append(
                    f"registry:{item.provider}:runtime-transport-method-mismatch"
                )
            if host_identities != item.host_mutation_identities:
                violations.append(
                    f"registry:{item.provider}:runtime-host-identities-mismatch"
                )

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


def _iter_code_files(
    root: Path,
    *,
    _code_suffixes: frozenset[str] = _CODE_SUFFIXES,
) -> Iterable[Path]:
    for file in root.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in _code_suffixes:
            continue
        parts = set(file.parts)
        if ".git" in parts or "node_modules" in parts or "__pycache__" in parts:
            continue
        yield file


_QUOTED_STRING = re.compile(
    r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')""",
    re.DOTALL,
)


def _compact_provider_text(value: str) -> str:
    """Conservative lexical view defeating simple split-string construction."""
    return "".join(ch for ch in value if ch.isalnum() or ch == "_")


def _literal_stream(source: str) -> str:
    """Concatenate quoted literal payloads across supported source languages."""
    return "".join(match.group(0)[1:-1] for match in _QUOTED_STRING.finditer(source))


def _contains_provider_marker(source: str, marker: str) -> bool:
    if marker in source:
        return True
    compact_marker = _compact_provider_text(marker)
    if not compact_marker:
        return False
    if compact_marker in _compact_provider_text(source):
        return True
    return compact_marker in _compact_provider_text(_literal_stream(source))


def find_bypasses(
    repository_root: str | Path,
    *,
    validate_manifest: bool = True,
    _validate_registry=validate_registry,
    _iter_files=_iter_code_files,
    _python_scan=_python_call_violations,
    _marker_match=_contains_provider_marker,
    _provider_markers: tuple[str, ...] = PROVIDER_MARKERS,
    _low_level_primitives: frozenset[str] = frozenset(_LOW_LEVEL_PRIMITIVES),
    _chain_files: frozenset[str] = frozenset(_CHAIN_FILES),
    _provider_method_allowed: frozenset[str] = frozenset(_PROVIDER_METHOD_ALLOWED),
    _marker_allowed: frozenset[str] = frozenset(_MARKER_ALLOWED),
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
        violations.extend(_validate_registry(root))

    for file in _iter_files(root):
        rel = file.relative_to(root).as_posix()
        if _is_test(rel) or rel in _low_level_primitives:
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
            if rel not in _chain_files:
                for label in _python_scan(tree):
                    violations.append(f"{rel}:{label}")
            elif rel not in _provider_method_allowed:
                for label in _python_scan(tree):
                    if label.startswith("provider-transport-method:") or label.startswith("dynamic-provider-transport-method:"):
                        violations.append(f"{rel}:{label}")

        if rel not in _marker_allowed:
            for marker in _provider_markers:
                if _marker_match(source, marker):
                    violations.append(f"{rel}:provider-marker:{marker}")

    return sorted(set(violations))


def registered_provider_names(
    _trusted_adapters: tuple[Adapter, ...] = ADAPTERS,
) -> tuple[str, ...]:
    return tuple(item.provider for item in _trusted_adapters)


def registered_host_mutation_identities(
    _trusted_identities: frozenset[str] = _HOST_MUTATION_IDENTITIES,
) -> tuple[str, ...]:
    return tuple(sorted(_trusted_identities))
