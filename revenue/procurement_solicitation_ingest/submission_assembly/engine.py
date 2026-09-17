"""Compatibility facade for the procurement submission assembly compiler."""
from .schema import *  # re-export the public schema contract
from .compiler import compile_manifest, verify
from .custody import artifact_loader_from_root
from .cli import build_parser, main

__all__ = [
    "AssemblyError", "ArtifactCustodyError", "INPUT_SCHEMA", "MANIFEST_SCHEMA", "RECEIPT_SCHEMA",
    "TRUTH_BOUNDARY", "SOURCE_AUTHORITY", "READY", "MISSING", "CONFLICT", "DEADLINE",
    "AUTHORITY", "canon", "sha256", "load_strict_json", "normalize_input",
    "compile_manifest", "verify", "artifact_loader_from_root", "build_parser", "main",
]
