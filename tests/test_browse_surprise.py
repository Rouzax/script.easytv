#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the browse window's "Surprise Me" pick.

Covers pick_surprise_position (which row the button lands on) and
BrowseWindow._play_surprise (what the window does with that row).
"""
import pytest

from resources.lib.ui.browse_window import (
    SURPRISE_BUTTON_ID,
    BrowseWindow,
    pick_surprise_position,
)

# ---------------------------------------------------------------------------
# pick_surprise_position
# ---------------------------------------------------------------------------


def test_no_rows_gives_no_pick():
    """An empty browse list has nothing to surprise the user with."""
    assert pick_surprise_position([]) is None


def test_rows_without_an_episode_are_not_eligible():
    """Rows whose EpisodeID property is empty cannot be played."""
    assert pick_surprise_position(['', '', '']) is None


def test_single_playable_row_is_always_picked():
    assert pick_surprise_position(['', '77', '']) == 1


def test_only_playable_rows_are_ever_picked():
    """Rows without an episode id stay out of the pool across many draws."""
    ids = ['', '101', '', '102', '']
    seen = {pick_surprise_position(ids) for _ in range(200)}
    assert seen == {1, 3}


def test_every_playable_row_can_be_picked():
    """The pick spans the whole list, not just the first few rows."""
    ids = [str(100 + i) for i in range(10)]
    seen = {pick_surprise_position(ids) for _ in range(500)}
    assert seen == set(range(10))


# ---------------------------------------------------------------------------
# BrowseWindow._play_surprise
# ---------------------------------------------------------------------------


class _FakeListItem:
    def __init__(self, episode_id):
        self._episode_id = episode_id

    def getProperty(self, key):
        return self._episode_id if key == 'EpisodeID' else ''


class _FakeListControl:
    def __init__(self, episode_ids):
        self._items = [_FakeListItem(e) for e in episode_ids]

    def size(self):
        return len(self._items)

    def getListItem(self, index):
        return self._items[index]


class _FakeLogger:
    def __init__(self):
        self.calls = []

    def _record(self, level, msg, **fields):
        self.calls.append((level, msg, fields))

    def info(self, msg, **fields):
        self._record('info', msg, **fields)

    def debug(self, msg, **fields):
        self._record('debug', msg, **fields)

    def warning(self, msg, **fields):
        self._record('warning', msg, **fields)


class _StubWindow:
    """Duck-typed stand-in so _play_surprise runs without a Kodi window."""

    def __init__(self, episode_ids):
        self.name_list = _FakeListControl(episode_ids)
        self._log = _FakeLogger()
        self._selected_show = None
        self._play_requested = False
        self.closed = False

    def close(self):
        self.closed = True


@pytest.fixture
def play_surprise():
    return BrowseWindow._play_surprise


def test_play_surprise_requests_playback_of_a_listed_episode(play_surprise):
    window = _StubWindow(['101', '102', '103'])

    play_surprise(window)

    assert window._selected_show in (101, 102, 103)
    assert window._play_requested is True
    assert window.closed is True


def test_play_surprise_selects_an_int_not_a_string(play_surprise):
    """browse_mode passes selected_show to int(), so keep the click path's type."""
    window = _StubWindow(['205'])

    play_surprise(window)

    assert window._selected_show == 205
    assert isinstance(window._selected_show, int)


def test_play_surprise_skips_rows_without_an_episode(play_surprise):
    window = _StubWindow(['', '303', ''])

    play_surprise(window)

    assert window._selected_show == 303


def test_play_surprise_on_an_empty_list_does_nothing(play_surprise):
    window = _StubWindow([])

    play_surprise(window)

    assert window._selected_show is None
    assert window._play_requested is False
    assert window.closed is False


def test_play_surprise_with_no_playable_row_does_nothing(play_surprise):
    window = _StubWindow(['', ''])

    play_surprise(window)

    assert window._play_requested is False
    assert window.closed is False


def test_play_surprise_logs_the_pick(play_surprise):
    window = _StubWindow(['101', '102'])

    play_surprise(window)

    events = [f.get('event') for _, _, f in window._log.calls]
    assert 'ui.surprise' in events


def test_surprise_button_id_avoids_kodi_reserved_ids():
    """Kodi reserves 2-4 in WindowXMLDialog; ID 3 swallows onClick entirely."""
    assert SURPRISE_BUTTON_ID >= 5
