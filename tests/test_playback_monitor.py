"""Tests for resources/lib/service/playback_monitor.py — playback handling."""
from unittest.mock import MagicMock, patch

from resources.lib.service.playback_monitor import PlaybackMonitor


def _make_monitor():
    """A PlaybackMonitor with mocked callbacks (no Kodi runtime needed)."""
    return PlaybackMonitor(
        window=MagicMock(),
        get_settings=MagicMock(),
        get_random_order_shows=MagicMock(return_value=[]),
        on_refresh_show=MagicMock(),
        clear_target=MagicMock(),
        get_nextprompt_info=MagicMock(),
        set_nextprompt_info=MagicMock(),
        logger=MagicMock(),
    )


class TestDeferredMissedCheck:
    """The missed-episode warning must run at onAVStarted, not onPlayBackStarted.

    At onPlayBackStarted the player is still loading, so the pause
    (Player.PlayPause play=false) is lost when playback actually begins
    (verified live). onAVStarted fires once the stream is playing, where the
    pause sticks - the same deferral the resume-seek already uses.
    """

    def test_onavstarted_runs_pending_missed_check(self):
        monitor = _make_monitor()
        monitor._pending_resume_seek = None
        monitor._pending_movie_random_start = False
        monitor._pending_missed_check = (7, 16, "Barry")
        with patch.object(monitor, '_check_previous_episode') as mcheck:
            monitor.onAVStarted()
        mcheck.assert_called_once_with(7, 16, "Barry")
        assert monitor._pending_missed_check is None

    def test_onavstarted_noop_without_pending_missed_check(self):
        monitor = _make_monitor()
        monitor._pending_resume_seek = None
        monitor._pending_movie_random_start = False
        monitor._pending_missed_check = None
        with patch.object(monitor, '_check_previous_episode') as mcheck:
            monitor.onAVStarted()
        mcheck.assert_not_called()
