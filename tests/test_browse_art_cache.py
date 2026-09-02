#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for browse mode's show-art session cache.

The art query costs ~1.2s against a large MySQL library, so it is fetched once
per Kodi session and cached to window properties. Two guarantees keep that
safe, and both are load-bearing:

  - an empty or posterless result must NOT latch the session flag, or the list
    renders with no images for the rest of the session (GitHub issue #2)
  - a set flag must skip the query, which is what makes it a once-per-session
    cost rather than a per-launch one
"""
from unittest.mock import MagicMock, patch

from resources.lib.constants import PROP_ART_FETCHED


def _shows(*posters):
    return {'tvshows': [
        {'tvshowid': i, 'art': ({'poster': p} if p else {})}
        for i, p in enumerate(posters, start=1)
    ]}


class TestArtSessionFlag:

    @patch('resources.lib.playback.browse_mode.json_query')
    @patch('resources.lib.playback.browse_mode.WINDOW')
    def test_empty_result_does_not_latch_the_flag(self, mock_window, mock_query):
        """Issue #2: latching on an empty result left browse imageless."""
        from resources.lib.playback.browse_mode import _fetch_show_art
        mock_window.getProperty.return_value = ''
        mock_query.return_value = {'tvshows': []}

        _fetch_show_art(MagicMock())

        latched = [c for c in mock_window.setProperty.call_args_list
                   if c[0][0] == PROP_ART_FETCHED]
        assert latched == []

    @patch('resources.lib.playback.browse_mode.json_query')
    @patch('resources.lib.playback.browse_mode.WINDOW')
    def test_posterless_shows_do_not_latch_the_flag(self, mock_window, mock_query):
        from resources.lib.playback.browse_mode import _fetch_show_art
        mock_window.getProperty.return_value = ''
        mock_query.return_value = _shows(None, None)

        _fetch_show_art(MagicMock())

        latched = [c for c in mock_window.setProperty.call_args_list
                   if c[0][0] == PROP_ART_FETCHED]
        assert latched == []

    @patch('resources.lib.playback.browse_mode.json_query')
    @patch('resources.lib.playback.browse_mode.WINDOW')
    def test_real_art_latches_the_flag(self, mock_window, mock_query):
        from resources.lib.playback.browse_mode import _fetch_show_art
        mock_window.getProperty.return_value = ''
        mock_query.return_value = _shows('image://poster1/', None)

        _fetch_show_art(MagicMock())

        mock_window.setProperty.assert_any_call(PROP_ART_FETCHED, 'true')

    @patch('resources.lib.playback.browse_mode.json_query')
    @patch('resources.lib.playback.browse_mode.WINDOW')
    def test_set_flag_skips_the_query(self, mock_window, mock_query):
        """This is the whole point of the cache: no second ~1.2s query."""
        from resources.lib.playback.browse_mode import _fetch_show_art
        mock_window.getProperty.return_value = 'true'

        _fetch_show_art(MagicMock())

        mock_query.assert_not_called()
