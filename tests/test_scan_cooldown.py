"""Tests for library scan cooldown guard."""
import time
from unittest.mock import MagicMock

from resources.lib.service.library_monitor import LibraryMonitor


def _make_monitor():
    """Create a LibraryMonitor with mocked dependencies."""
    window = MagicMock()
    on_settings_changed = MagicMock()
    get_random_order_shows = MagicMock(return_value=[])
    on_refresh_show = MagicMock()
    on_playing_episode_watched = MagicMock()

    monitor = LibraryMonitor(
        window=window,
        on_settings_changed=on_settings_changed,
        get_random_order_shows=get_random_order_shows,
        on_refresh_show=on_refresh_show,
        on_playing_episode_watched=on_playing_episode_watched,
    )
    return monitor


class TestScanCooldown:
    """Tests for scan cooldown state tracking in LibraryMonitor."""

    def test_initial_state_no_cooldown(self):
        """Monitor starts with no pending cooldown."""
        monitor = _make_monitor()
        assert monitor.scan_finished_at is None
        assert not monitor.is_scanning

    def test_scan_started_sets_flag(self):
        """onScanStarted sets scanning flag for video library."""
        monitor = _make_monitor()
        monitor.onScanStarted('video')
        assert monitor.is_scanning

    def test_scan_started_ignores_music(self):
        """onScanStarted ignores music library scans."""
        monitor = _make_monitor()
        monitor.onScanStarted('music')
        assert not monitor.is_scanning

    def test_scan_finished_records_timestamp(self):
        """onScanFinished records the finish time and clears scanning flag."""
        monitor = _make_monitor()
        monitor.onScanStarted('video')
        monitor.onScanFinished('video')
        assert monitor.scan_finished_at is not None
        assert not monitor.is_scanning

    def test_scan_finished_does_not_set_lib_update_flag(self):
        """onScanFinished does not trigger an immediate refresh; daemon polls instead."""
        monitor = _make_monitor()
        monitor.onScanFinished('video')
        # No immediate action: consume_scan_update must return False right away
        assert not monitor.consume_scan_update()

    def test_scan_finished_clears_art_cache(self):
        """onScanFinished still clears the art cache property."""
        monitor = _make_monitor()
        monitor.onScanFinished('video')
        monitor._window.clearProperty.assert_called()

    def test_scan_finished_ignores_music(self):
        """onScanFinished ignores music library scans."""
        monitor = _make_monitor()
        monitor.onScanFinished('music')
        assert monitor.scan_finished_at is None

    def test_consecutive_scans_update_timestamp(self):
        """Each onScanFinished updates the timestamp (latest wins)."""
        monitor = _make_monitor()
        monitor.onScanFinished('video')
        first = monitor.scan_finished_at
        time.sleep(0.01)
        monitor.onScanFinished('video')
        assert monitor.scan_finished_at > first

    def test_consume_scan_update_returns_true_after_cooldown(self):
        """consume_scan_update returns True when cooldown has elapsed."""
        monitor = _make_monitor()
        monitor.onScanFinished('video')
        # Fake the timestamp to be far enough in the past
        monitor.scan_finished_at = time.monotonic() - 10.0
        assert monitor.consume_scan_update()
        assert monitor.scan_finished_at is None

    def test_consume_scan_update_returns_false_during_cooldown(self):
        """consume_scan_update returns False when cooldown hasn't elapsed."""
        monitor = _make_monitor()
        monitor.onScanFinished('video')
        # Just happened, cooldown not elapsed
        assert not monitor.consume_scan_update()
        assert monitor.scan_finished_at is not None

    def test_consume_scan_update_returns_false_during_active_scan(self):
        """consume_scan_update returns False while a scan is in progress."""
        monitor = _make_monitor()
        monitor.onScanFinished('video')
        monitor.scan_finished_at = time.monotonic() - 10.0
        monitor.onScanStarted('video')
        assert not monitor.consume_scan_update()

    def test_consume_scan_update_returns_false_when_no_scan(self):
        """consume_scan_update returns False when no scan has occurred."""
        monitor = _make_monitor()
        assert not monitor.consume_scan_update()


def _make_daemon():
    """Create a minimal ServiceDaemon for testing scan cooldown integration."""
    from resources.lib.service.daemon import ServiceDaemon

    daemon = object.__new__(ServiceDaemon)
    daemon._log = MagicMock()
    daemon._window = MagicMock()
    daemon._player = MagicMock()
    daemon._player._playing_showid = False
    daemon._sync_enabled = False
    daemon._sync_tick_counter = 0
    daemon._last_sync_rev = 0

    class FakeState:
        shows_with_next_episodes = []
        target = False
        nextprompt_info = {}

    daemon._state = FakeState()
    daemon._episode_tracker = MagicMock()
    daemon._settings = MagicMock()
    daemon._addon = MagicMock()
    daemon._all_shows_list = []
    daemon._position_check_count = 0
    daemon._initial_limit = 30
    daemon._current_show_id = None
    daemon._pending_next_episode = False
    daemon._is_random_show = False

    daemon._monitor = LibraryMonitor(
        window=daemon._window,
        on_settings_changed=MagicMock(),
        get_random_order_shows=MagicMock(return_value=[]),
        on_refresh_show=MagicMock(),
        on_playing_episode_watched=MagicMock(),
    )

    return daemon


class TestDaemonScanCooldownIntegration:
    """Tests for scan cooldown integration in daemon _process_events."""

    def test_no_refresh_during_cooldown(self):
        """Daemon does not refresh shows while cooldown is pending."""
        daemon = _make_daemon()
        daemon._retrieve_all_show_ids = MagicMock()
        daemon._monitor.onScanFinished('video')
        daemon._process_events()
        daemon._retrieve_all_show_ids.assert_not_called()

    def test_refresh_after_cooldown(self):
        """Daemon refreshes shows after cooldown elapses."""
        daemon = _make_daemon()
        daemon._monitor.onScanFinished('video')
        daemon._monitor.scan_finished_at = time.monotonic() - 10.0
        daemon._retrieve_all_show_ids = MagicMock()
        daemon.refresh_show_episodes = MagicMock()

        daemon._process_events()

        daemon._retrieve_all_show_ids.assert_called_once()
        daemon.refresh_show_episodes.assert_called_once()

    def test_no_refresh_while_scan_active(self):
        """Daemon does not refresh while a scan is still in progress."""
        daemon = _make_daemon()
        daemon._monitor.onScanFinished('video')
        daemon._monitor.scan_finished_at = time.monotonic() - 10.0
        daemon._monitor.onScanStarted('video')
        daemon._retrieve_all_show_ids = MagicMock()

        daemon._process_events()

        daemon._retrieve_all_show_ids.assert_not_called()

    def test_rapid_scans_batch_into_single_refresh(self):
        """Multiple rapid scans result in only one refresh."""
        daemon = _make_daemon()
        daemon._retrieve_all_show_ids = MagicMock()
        daemon.refresh_show_episodes = MagicMock()

        for _ in range(5):
            daemon._monitor.onScanStarted('video')
            daemon._monitor.onScanFinished('video')

        daemon._process_events()
        daemon._retrieve_all_show_ids.assert_not_called()

        daemon._monitor.scan_finished_at = time.monotonic() - 10.0
        daemon._process_events()

        daemon._retrieve_all_show_ids.assert_called_once()
        daemon.refresh_show_episodes.assert_called_once()
