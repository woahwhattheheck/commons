"""SYNTHETIC FIXTURE. Expected: SELF_SCOPED — it removes only what it created."""
import shutil
import tempfile


def verify_in_scratch(payload):
    scratch = tempfile.mkdtemp(prefix="fixture-")
    try:
        return len(payload)
    finally:
        shutil.rmtree(scratch)
