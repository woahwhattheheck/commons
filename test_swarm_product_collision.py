"""Root CI-battery entrypoint for the product collision test suite.

The Commons battery discovers root ``test_*.py`` files. Keep the detailed suite
under ``tests/`` for focused unittest invocation while making that same suite
part of the repository-wide source-linked battery.
"""
from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent / "tests" / "test_swarm_product_collision.py"),
        run_name="__main__",
    )
