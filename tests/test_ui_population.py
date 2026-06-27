#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the show-selection read logic in ui/main.py.

Focuses on _read_selected_shows: verifying that clones use their own
'selection' setting while the main addon reads the EasyTV.selection
window property.
"""
from unittest.mock import MagicMock

from resources.lib.ui import main as ui_main
from resources.lib.ui.main import _read_selected_shows


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
    monkeypatch.setattr(ui_main, 'window', _FakeWindow({"EasyTV.selection": "[1, 2, 3]"}), raising=False)
    # _read_selected_shows builds its own Window; monkeypatch the class read instead:
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
