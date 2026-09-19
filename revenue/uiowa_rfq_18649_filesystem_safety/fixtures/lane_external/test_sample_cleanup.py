"""SYNTHETIC FIXTURE. A test module, but the target is still caller-supplied.

Expected: REVIEW_REQUIRED, not TEST_CONTEXT. Being in a test file lowers the
priority of a self-scoped cleanup; it does not excuse removing a path somebody
else handed in.
"""
import shutil
import tempfile


def helper_cleanup(supplied_path):
    shutil.rmtree(supplied_path)


def helper_own_temp():
    scratch = tempfile.mkdtemp()
    shutil.rmtree(scratch)
