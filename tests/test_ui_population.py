#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the show-selection and random-order read logic in ui/main.py.

Focuses on _read_selected_shows and _read_random_order_shows: verifying
that clones use their own settings while the main addon reads shared
window properties.
"""
from unittest.mock import MagicMock

from resources.lib.ui.main import _read_random_order_shows, _read_selected_shows


def _addon(addon_id, settings=None):
    a = MagicMock()
    a.getAddonInfo.return_value = addon_id
    s = settings or {}
    a.getSetting.side_effect = lambda k: s.get(k, '')
    return a


class _FakeWindow:
    def __init__(self, props): self._p = props
    def getProperty(self, k): return self._p.get(k, '')


def test_main_addon_reads_window_property(monkeypatch):
    monkeypatch.setattr('resources.lib.ui.main.xbmcgui.Window',
                        lambda _id: _FakeWindow({"EasyTV.selection": "[1, 2, 3]"}))
    assert sorted(_read_selected_shows(_addon('script.easytv'))) == [1, 2, 3]


def test_clone_reads_its_own_setting_not_window_property(monkeypatch):
    monkeypatch.setattr('resources.lib.ui.main.xbmcgui.Window',
                        lambda _id: _FakeWindow({"EasyTV.selection": "[1, 2, 3]"}))
    addon = _addon('script.easytv.kids', {'selection': "{'9': 'Bluey'}"})
    assert _read_selected_shows(addon) == [9]   # own setting, NOT the window's [1,2,3]


def test_clone_empty_selection_is_empty_list():
    assert _read_selected_shows(_addon('script.easytv.kids', {'selection': "none"})) == []


def test_clone_reads_its_own_random_order_setting(monkeypatch):
    monkeypatch.setattr('resources.lib.ui.main.xbmcgui.Window',
                        lambda _id: _FakeWindow({"EasyTV.random_order_shows": "[1, 2]"}))
    addon = _addon('script.easytv.kids', {'random_order_shows': "{'9': 'Bluey'}"})
    assert _read_random_order_shows(addon) == [9]   # own setting, not window [1,2]


def test_main_addon_random_order_from_window_property(monkeypatch):
    monkeypatch.setattr('resources.lib.ui.main.xbmcgui.Window',
                        lambda _id: _FakeWindow({"EasyTV.random_order_shows": "[1, 2]"}))
    assert sorted(_read_random_order_shows(_addon('script.easytv'))) == [1, 2]
