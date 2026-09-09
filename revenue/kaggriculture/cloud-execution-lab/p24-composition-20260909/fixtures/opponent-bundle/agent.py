"""Tiny dependency-bearing opponent used only for manifest verification tests."""
from helper import passive_action


def agent(observation, configuration):
    del observation, configuration
    return passive_action()
