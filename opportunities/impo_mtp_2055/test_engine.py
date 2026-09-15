"""Aggregate the split IMPO MTP 2055 test suite for one stable CI entrypoint."""

import unittest

from .test_cli import CliTests
from .test_compilation import CompilationTests
from .test_validation import ValidationTests
from .test_verification import VerificationTests

__all__ = ["CliTests", "CompilationTests", "ValidationTests", "VerificationTests"]

if __name__ == "__main__":
    unittest.main()
