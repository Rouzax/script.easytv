"""
Tests for clone-mode random-order resolution in build_random_playlist / _process_tv_candidate.

For clones, the first-episode UNWATCHED pick must be resolved locally from
the show's broadcast pools (ondeck_list / offdeck_list window properties)
instead of the service's pre-cached EpisodeID.

IMPORTANT: Kodistubs are inert - the module-global WINDOW in random_player does
NOT persist setProperty calls.  Tests monkeypatch rp.WINDOW with a _FakeWindow
so getProperty returns canned values.
"""
import random

from resources.lib.constants import EPISODE_SELECTION_UNWATCHED
from resources.lib.playback import random_player as rp
from resources.lib.playback.random_player import (
    RandomPlaylistConfig,
    _process_tv_candidate,
)
from resources.lib.utils import get_logger


class _FakeWindow:
    """Minimal window stub whose getProperty returns canned values."""

    def __init__(self, props: dict) -> None:
        self._p = props

    def getProperty(self, k: str) -> str:
        return self._p.get(k, '')


def _cfg() -> RandomPlaylistConfig:
    """Build a minimal config for these tests (all other fields use defaults)."""
    return RandomPlaylistConfig(
        episode_selection=EPISODE_SELECTION_UNWATCHED,
        multiple_shows=False,
    )


def test_clone_random_show_picks_from_pool(monkeypatch):
    """When clone_mode=True and the show is in random_order_shows, the episode
    must come from ondeck_list / offdeck_list, not the stale EpisodeID cache."""
    monkeypatch.setattr(rp, 'WINDOW', _FakeWindow({
        "EasyTV.55.EpisodeID": "999",        # service cached pick - must NOT be used
        "EasyTV.55.ondeck_list": "[10, 11]",
        "EasyTV.55.offdeck_list": "[3]",
    }))
    random.seed(0)
    eid, _ = _process_tv_candidate(
        55, {}, ['t55'], [55], _cfg(), get_logger('test'),
        clone_mode=True,
    )
    assert eid in {10, 11, 3}, f"Expected episode from pool {{10, 11, 3}}, got {eid}"


def test_clone_sequential_show_picks_ondeck_head(monkeypatch):
    """When clone_mode=True but the show is NOT in random_order_shows, the first
    ondeck episode is returned (sequential order, not random)."""
    monkeypatch.setattr(rp, 'WINDOW', _FakeWindow({
        "EasyTV.55.EpisodeID": "999",
        "EasyTV.55.ondeck_list": "[10, 11]",
        "EasyTV.55.offdeck_list": "[3]",
    }))
    eid, _ = _process_tv_candidate(
        55, {}, ['t55'], [], _cfg(), get_logger('test'),
        clone_mode=True,
    )
    # random_order_shows=[] so show 55 is sequential: returns ondeck_list[0] = 10
    assert eid == 10


def test_clone_returns_none_when_pools_empty(monkeypatch):
    """When clone_mode=True and both pools are empty, _process_tv_candidate
    must return (None, False) and remove the show from candidate_list."""
    monkeypatch.setattr(rp, 'WINDOW', _FakeWindow({
        "EasyTV.55.EpisodeID": "999",        # ignored in clone_mode
        "EasyTV.55.ondeck_list": "[]",
        "EasyTV.55.offdeck_list": "[]",
    }))
    candidate_list = ['t55']
    eid, _ = _process_tv_candidate(
        55, {}, candidate_list, [], _cfg(), get_logger('test'),
        clone_mode=True,
    )
    assert eid is None
    assert 't55' not in candidate_list


def test_main_addon_unchanged_uses_cached_episode_id(monkeypatch):
    """When clone_mode is omitted (defaults False), the original main-addon
    path reads EpisodeID from the window cache unchanged."""
    monkeypatch.setattr(rp, 'WINDOW', _FakeWindow({"EasyTV.55.EpisodeID": "999"}))
    eid, _ = _process_tv_candidate(55, {}, ['t55'], [], _cfg(), get_logger('test'))
    assert eid == 999, f"Expected 999 from EpisodeID cache, got {eid}"


def test_main_addon_returns_none_when_no_episode_id(monkeypatch):
    """Without clone_mode, a missing EpisodeID still returns (None, False)."""
    monkeypatch.setattr(rp, 'WINDOW', _FakeWindow({}))
    candidate_list = ['t55']
    eid, _ = _process_tv_candidate(55, {}, candidate_list, [], _cfg(), get_logger('test'))
    assert eid is None
    assert 't55' not in candidate_list
