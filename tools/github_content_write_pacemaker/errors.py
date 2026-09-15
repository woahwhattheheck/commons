"""Deterministic pacemaker error types."""


class PacemakerError(RuntimeError):
    """Base class for deterministic refusals."""


class IntentConflict(PacemakerError):
    """A stable key was reused for different semantics."""


class StoreInvariantError(PacemakerError):
    """Persistent state no longer satisfies the recorded contract."""


class NoDispatchableMutation(PacemakerError):
    """No queued mutation is eligible at the current time."""


class AmbiguousOutcome(PacemakerError):
    """A prior provider effect requires external readback."""
