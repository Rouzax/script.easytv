#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for clone browse-mode row overrides.

Verifies that _clone_row_overrides returns None when the locally resolved
on-deck episode matches the cached pick, and returns a metadata dict (without
any shared setProperty writes) when the pick diverges.
"""
import random

from resources.lib.ui import browse_window as bw
from resources.lib.ui.browse_window import _clone_row_overrides


class _FakeWindow:
    def __init__(self, props):
        self._p = props

    def getProperty(self, k):
        return self._p.get(k, '')


def test_no_override_when_resolved_equals_cache(monkeypatch):
    """Sequential clone resolves ondeck[0]=10 which equals the cache -> no fetch."""
    monkeypatch.setattr(bw, 'WINDOW', _FakeWindow({
        "EasyTV.7.EpisodeID": "10",
        "EasyTV.7.ondeck_list": "[10, 11]",
        "EasyTV.7.offdeck_list": "[]",
    }))
    # show 7 is NOT in random_order_shows, so sequential resolution gives ondeck[0]=10 == cache
    assert _clone_row_overrides(7, random_order_shows=[]) is None


def test_override_fetches_for_divergent_random_pick(monkeypatch):
    """Random pick from [10,11,12] diverges from cached id 999 -> fetch and return override."""
    monkeypatch.setattr(bw, 'WINDOW', _FakeWindow({
        "EasyTV.7.EpisodeID": "999",      # outside the pool -> divergence guaranteed
        "EasyTV.7.ondeck_list": "[10, 11, 12]",
        "EasyTV.7.offdeck_list": "[]",
    }))
    captured = {}

    def fake_query(q, *a, **k):
        captured['id'] = q['params']['episodeid']
        return {
            'episodedetails': {
                'episodeid': captured['id'],
                'title': 'X',
                'season': 2,
                'episode': 5,
                'plot': 'p',
                'file': 'f',
                'art': {},
                'resume': {'position': 30, 'total': 100},
            }
        }

    monkeypatch.setattr('resources.lib.ui.browse_window.json_query', fake_query)
    random.seed(0)
    out = _clone_row_overrides(7, random_order_shows=[7])
    assert out is not None
    assert out['episode_id'] in {10, 11, 12}
    assert captured['id'] == out['episode_id']   # fetched the resolved id
    assert out['episodeno'] == 's02e05'           # derived from season/episode
    assert out['percentplayed'] == 30             # derived from resume 30/100
