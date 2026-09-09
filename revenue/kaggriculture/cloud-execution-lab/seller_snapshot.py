# SPDX-License-Identifier: Apache-2.0
"""Compact, detached public history for the existing frozen SELL observer.

This evolves QUICKSTEP's landed seller snapshot: E02 still retains only public
rival state, but now includes the public farmer/hand positions needed to bound a
possible harvest's earliest legal shed arrival. No private inventory is copied.
"""
from copy import deepcopy
from typing import Any, Mapping


def seller_public_observation(
    observation: Mapping[str, Any] | None, *, copy_tiles: bool = True
) -> dict[str, Any] | None:
    """Return the seller observer's compact two-farm-shaped public snapshot."""
    if observation is None:
        return None
    player = int(observation['player'])
    rival = 1 - player
    source = observation['farms'][rival]
    if copy_tiles:
        public = {
            'tiles': deepcopy(source['tiles']),
            'farmer': deepcopy(source.get('farmer')),
            'hands': deepcopy(source.get('hands', [])),
        }
    else:
        public = {
            'tiles': source['tiles'],
            'farmer': source.get('farmer'),
            'hands': source.get('hands', []),
        }
    empty = {'tiles': [], 'farmer': None, 'hands': []}
    farms = [dict(empty), dict(empty)]
    farms[rival] = public
    return {'step': int(observation['step']), 'player': player, 'farms': farms}
