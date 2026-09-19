"""SYNTHETIC FIXTURE. Expected: REVIEW_REQUIRED on both calls.

The point of the fixture: neither call is obviously wrong, and that is exactly
why a person has to confirm the target is what they meant.
"""
import os
import shutil
import sys


def clean_workspace(workspace):
    # The caller chooses what gets removed.
    shutil.rmtree(workspace)


def reset_from_argv():
    shutil.rmtree(sys.argv[1])


def drop_named(root, name):
    os.remove(os.path.join(root, name))
