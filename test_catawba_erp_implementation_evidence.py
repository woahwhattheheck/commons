from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parent / "revenue" / "catawba_erp_implementation_evidence" / "tests" / "test_acceptance.py"

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
