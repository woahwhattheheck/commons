"""Expose the complete offline source-preflight proof to root test discovery.

Run normally and with python -O. Recovery tests exercise real CLI subprocesses
explicitly in normal, -O and -OO modes; no provider is called by this suite.
"""
from tools.deploy_transport_preflight.test_preflight import PreflightTests
from tools.deploy_transport_preflight.test_recovery import RecoveryTests

__all__ = ["PreflightTests", "RecoveryTests"]
