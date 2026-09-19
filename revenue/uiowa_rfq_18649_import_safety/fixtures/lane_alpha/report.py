"""Fixture lane ALPHA. Synthetic. Shares a module name with lane BETA.

The two fixtures return DIFFERENT values on purpose. A fixture where both
lanes raise, or both return the same thing, cannot detect this bug: the
failure is that the wrong module loads silently and the caller gets a
plausible answer from the wrong lane.
"""

LANE = "alpha"


def summary():
    return "ALPHA: 3 findings"
