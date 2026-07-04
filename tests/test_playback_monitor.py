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


class TestResumeSeekSurvivesMissedCheck:
    """A pending resume seek must still run after the missed-episode check.

    Regression: the deferred missed check returned unconditionally from
    onAVStarted, dropping the pending resume seek. In browse mode both are
    scheduled for the same episode (the on-deck episode with a resume point),
    so the episode started from the beginning instead of resuming.
    """

    def test_resume_seek_runs_when_missed_check_does_not_replace(self):
        monitor = _make_monitor()
        monitor._pending_movie_random_start = False
        monitor._pending_missed_check = (7, 16, "Barry")
        monitor._pending_resume_seek = 900
        with patch.object(monitor, '_check_previous_episode', return_value=False) as mcheck, \
                patch('resources.lib.service.playback_monitor.json_query') as jq:
            monitor.onAVStarted()
        mcheck.assert_called_once_with(7, 16, "Barry")
        # The resume seek fired and was consumed.
        jq.assert_called_once()
        assert monitor._pending_resume_seek is None

    def test_resume_seek_dropped_when_missed_check_replaces_playback(self):
        monitor = _make_monitor()
        monitor._pending_movie_random_start = False
        monitor._pending_missed_check = (7, 16, "Barry")
        monitor._pending_resume_seek = 900

        # Faithfully simulate the real callee contract: on replace it drops the
        # now-stale seek itself (co-located side effect) and returns True.
        def _replace(*_args):
            monitor._pending_resume_seek = None
            return True

        with patch.object(monitor, '_check_previous_episode', side_effect=_replace) as mcheck, \
                patch('resources.lib.service.playback_monitor.json_query') as jq:
            monitor.onAVStarted()
        mcheck.assert_called_once_with(7, 16, "Barry")
        # onAVStarted stops after a replace: the stale seek for the abandoned
        # episode must not fire, and the callee already cleared it.
        jq.assert_not_called()
        assert monitor._pending_resume_seek is None


class TestPendingDeferralReset:
    """The onPlayBackStarted -> onAVStarted handoff fields reset together.

    All three ``_pending_*`` deferrals must clear at every playback boundary so
    a value queued for one item cannot leak into a later, unrelated playback
    when the stream that queued it never reached onAVStarted (aborted/failed
    playback). A leaked ``_pending_missed_check`` is the worst case: it would run
    the missed-episode check against the wrong show and could pause/replace an
    unrelated item.
    """

    def test_reset_clears_all_pending_handoff_state(self):
        monitor = _make_monitor()
        monitor._pending_movie_random_start = True
        monitor._pending_resume_seek = 900
        monitor._pending_missed_check = (7, 16, "Barry")
        monitor._reset_pending_deferrals()
        assert monitor._pending_movie_random_start is False
        assert monitor._pending_resume_seek is None
        assert monitor._pending_missed_check is None

    def test_stop_clears_leaked_missed_check(self):
        monitor = _make_monitor()
        monitor._pending_missed_check = (7, 16, "Barry")
        monitor._pending_resume_seek = 900
        monitor._pending_movie_random_start = True
        with patch.object(monitor, '_handle_playback_end'):
            monitor.onPlayBackStopped()
        # A stop must not leave a missed check queued for the next playback.
        assert monitor._pending_missed_check is None
        assert monitor._pending_resume_seek is None
        assert monitor._pending_movie_random_start is False
