import importlib.util
import pathlib

_PATH = (
    pathlib.Path(__file__).resolve().parent
    / "revenue"
    / "mcc_1017_27_ai_workspace_20260917"
    / "test_gate.py"
)
_SPEC = importlib.util.spec_from_file_location("mcc_1017_27_test_gate", _PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromModule(_MOD)
