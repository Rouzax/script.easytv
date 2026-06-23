"""Tests for daemon shared database sync mechanisms."""
from unittest.mock import MagicMock, patch

from resources.lib.constants import (
    PROP_SYNC_PENDING_SHOWS,
    SYNC_CHECK_INTERVAL_TICKS,
)
from resources.lib.data.storage import SharedDatabaseStorage


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_daemon():
    """Create a minimal ServiceDaemon-like object for testing sync methods.

    We test the methods in isolation rather than constructing a full
    ServiceDaemon (which needs Kodi runtime). This helper builds a
    lightweight stand-in with the attributes the sync methods read/write.
    """
    from resources.lib.service.daemon import ServiceDaemon

    daemon = object.__new__(ServiceDaemon)
    daemon._log = MagicMock()
    daemon._window = MagicMock()
    daemon._player = MagicMock()
    daemon._player._playing_showid = False
    daemon._sync_enabled = True
    daemon._sync_tick_counter = 0
    daemon._last_sync_rev = 0
    daemon._last_sync_updated_at = None

    class FakeState:
        shows_with_next_episodes = []
    daemon._state = FakeState()

    daemon._episode_tracker = MagicMock()
    daemon._settings = MagicMock()
    daemon._addon = MagicMock()
    daemon._all_shows_list = []
    daemon._position_check_count = 0
    daemon._initial_limit = 30

    return daemon


# ── _check_shared_db_sync ───────────────────────────────────────────────

class TestCheckSharedDbSync:
    """Tests for the periodic shared DB revision check."""

    @patch('resources.lib.service.daemon.get_storage')
    def test_skips_when_sync_disabled(self, mock_get_storage):
        """Should do nothing when multi-instance sync is off."""
        daemon = _make_daemon()
        daemon._sync_enabled = False
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS

        daemon._check_shared_db_sync()

        mock_get_storage.assert_not_called()

    @patch('resources.lib.service.daemon.get_storage')
    def test_skips_when_playback_active(self, mock_get_storage):
        """Should skip and log when a show is currently playing."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._player._playing_showid = 42

        daemon._check_shared_db_sync()

        mock_get_storage.assert_not_called()
        daemon._log.debug.assert_any_call(
            "Skipping shared DB sync (playback active)",
            event="sync.daemon_skip_playback",
        )

    @patch('resources.lib.service.daemon.get_storage')
    def test_skips_before_interval(self, mock_get_storage):
        """Should increment counter but not check before interval reached."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = 0

        daemon._check_shared_db_sync()

        assert daemon._sync_tick_counter == 1
        mock_get_storage.assert_not_called()

    @patch('resources.lib.service.daemon.get_storage')
    def test_resets_counter_after_check(self, mock_get_storage):
        """Counter should reset to 0 after performing a check."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 0
        mock_get_storage.return_value = storage

        daemon._check_shared_db_sync()

        assert daemon._sync_tick_counter == 0

    @patch('resources.lib.service.daemon.get_storage')
    def test_noop_when_revision_unchanged(self, mock_get_storage):
        """Should log unchanged and skip when revision matches."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 42
        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 42
        mock_get_storage.return_value = storage

        daemon._check_shared_db_sync()

        storage.get_tracked_show_ids.assert_not_called()
        daemon._log.debug.assert_any_call(
            "Shared DB revision unchanged",
            event="sync.daemon_unchanged",
            rev=42,
        )

    @patch('resources.lib.service.daemon.get_storage')
    def test_discovers_added_shows(self, mock_get_storage):
        """Should call refresh_show_episodes for shows in DB but not in daemon."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 10
        daemon._state.shows_with_next_episodes = [1, 2, 3]

        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 11
        storage.get_tracked_show_ids.return_value = ({1, 2, 3, 4, 5}, 11)
        # No changes among already-tracked shows.
        storage.db.get_show_ids_updated_since.return_value = (set(), None)
        mock_get_storage.return_value = storage

        with patch.object(daemon, 'refresh_show_episodes') as mock_refresh:
            daemon._check_shared_db_sync()

        mock_refresh.assert_called_once()
        called_ids = set(mock_refresh.call_args[1]['showids'])
        assert called_ids == {4, 5}
        assert mock_refresh.call_args[1]['bulk'] is False
        assert daemon._last_sync_rev == 11

    @patch('resources.lib.service.daemon.get_storage')
    def test_removes_shows_not_in_db(self, mock_get_storage):
        """Should remove shows from daemon state when gone from DB
        and not in Kodi library."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 10
        daemon._state.shows_with_next_episodes = [1, 2, 3]
        daemon._all_shows_list = [1, 2]  # show 3 not in Kodi either

        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 11
        storage.get_tracked_show_ids.return_value = ({1, 2}, 11)
        storage.db.get_show_ids_updated_since.return_value = (set(), None)
        mock_get_storage.return_value = storage

        with patch.object(daemon, 'refresh_show_episodes'):
            with patch.object(daemon, '_remove_from_shows_with_next_episodes') as mock_remove:
                daemon._check_shared_db_sync()

        mock_remove.assert_called_once_with(3)

    @patch('resources.lib.service.daemon.get_storage')
    def test_keeps_shows_still_in_kodi(self, mock_get_storage):
        """Should NOT remove a show from daemon if it still has episodes in Kodi,
        even when missing from shared DB."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 10
        daemon._state.shows_with_next_episodes = [1, 2, 3]
        daemon._all_shows_list = [1, 2, 3]  # show 3 still in Kodi

        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 11
        storage.get_tracked_show_ids.return_value = ({1, 2}, 11)
        storage.db.get_show_ids_updated_since.return_value = (set(), None)
        mock_get_storage.return_value = storage

        with patch.object(daemon, 'refresh_show_episodes'):
            with patch.object(daemon, '_remove_from_shows_with_next_episodes') as mock_remove:
                daemon._check_shared_db_sync()

        mock_remove.assert_not_called()

    @patch('resources.lib.service.daemon.get_storage')
    def test_skips_when_storage_unavailable(self, mock_get_storage):
        """Should skip gracefully when shared storage is not available."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = False
        mock_get_storage.return_value = storage

        daemon._check_shared_db_sync()

        storage.db.get_global_rev.assert_not_called()


# ── consume changed (watermark-driven) ─────────────────────────────────

class TestConsumeChangedShows:
    """Periodic sync must apply ANY row changed since last sync for shows
    tracked on both instances, via the updated_at watermark, without writing
    back to the shared DB (no rebroadcast)."""

    @patch('resources.lib.service.daemon.get_storage')
    def test_changed_tracked_show_consumed_without_rebroadcast(self, mock_get_storage):
        """A tracked show whose row changed since the watermark (e.g. a
        resume-only change with the same on-deck episode) is refreshed and
        re-categorised, with no DB write-back."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 631
        daemon._last_sync_updated_at = "2026-06-23 20:00:00"
        daemon._state.shows_with_next_episodes = [439]

        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 632
        storage.get_tracked_show_ids.return_value = ({439}, 632)
        storage.db.get_show_ids_updated_since.return_value = (
            {439}, "2026-06-23 21:00:00"
        )
        mock_get_storage.return_value = storage

        with patch.object(daemon, '_update_smartplaylist') as mock_sp:
            daemon._check_shared_db_sync()

        storage.get_ondeck_bulk.assert_called_once()
        bulk_args, bulk_kwargs = storage.get_ondeck_bulk.call_args
        assert set(bulk_args[0]) == {439}
        assert bulk_kwargs.get('refresh_display') is True
        mock_sp.assert_called_once_with(439, quiet=True)
        storage.set_ondeck.assert_not_called()
        storage.db.set_show_tracking.assert_not_called()
        assert daemon._last_sync_updated_at == "2026-06-23 21:00:00"
        assert daemon._last_sync_rev == 632

    @patch('resources.lib.service.daemon.get_storage')
    def test_no_changed_rows_does_not_consume(self, mock_get_storage):
        """When nothing changed since the watermark, no consume occurs."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 631
        daemon._last_sync_updated_at = "2026-06-23 20:00:00"
        daemon._state.shows_with_next_episodes = [439]

        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 632
        storage.get_tracked_show_ids.return_value = ({439}, 632)
        storage.db.get_show_ids_updated_since.return_value = (
            set(), "2026-06-23 20:00:00"
        )
        mock_get_storage.return_value = storage

        with patch.object(daemon, '_update_smartplaylist') as mock_sp:
            daemon._check_shared_db_sync()

        storage.get_ondeck_bulk.assert_not_called()
        mock_sp.assert_not_called()
        storage.set_ondeck.assert_not_called()

    @patch('resources.lib.service.daemon.get_storage')
    def test_changed_but_untracked_show_not_consumed(self, mock_get_storage):
        """A changed row not tracked locally is left to the add branch,
        not double-processed by the consume path."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 631
        daemon._last_sync_updated_at = "2026-06-23 20:00:00"
        daemon._state.shows_with_next_episodes = [439]

        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 632
        # 439 still tracked; 999 is a new show only present in the changed set
        storage.get_tracked_show_ids.return_value = ({439, 999}, 632)
        storage.db.get_show_ids_updated_since.return_value = (
            {999}, "2026-06-23 21:00:00"
        )
        mock_get_storage.return_value = storage

        with patch.object(daemon, 'refresh_show_episodes'):
            with patch.object(daemon, '_update_smartplaylist') as mock_sp:
                daemon._check_shared_db_sync()

        storage.get_ondeck_bulk.assert_not_called()
        mock_sp.assert_not_called()

    @patch('resources.lib.service.daemon.get_storage')
    def test_random_order_show_consumed_not_reshuffled(self, mock_get_storage):
        """A changed random-order show is consumed (adopted verbatim), never
        routed through refresh_show_episodes (which would reshuffle/rebroadcast)."""
        daemon = _make_daemon()
        daemon._sync_tick_counter = SYNC_CHECK_INTERVAL_TICKS
        daemon._last_sync_rev = 631
        daemon._last_sync_updated_at = "2026-06-23 20:00:00"
        daemon._state.shows_with_next_episodes = [439]
        daemon._settings.random_order_shows = {439}

        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.is_available.return_value = True
        storage.db = MagicMock()
        storage.db.get_global_rev.return_value = 632
        storage.get_tracked_show_ids.return_value = ({439}, 632)
        storage.db.get_show_ids_updated_since.return_value = (
            {439}, "2026-06-23 21:00:00"
        )
        mock_get_storage.return_value = storage

        with patch.object(daemon, 'refresh_show_episodes') as mock_refresh:
            with patch.object(daemon, '_update_smartplaylist'):
                daemon._check_shared_db_sync()

        for call in mock_refresh.call_args_list:
            assert 439 not in (call.kwargs.get('showids') or [])
        storage.get_ondeck_bulk.assert_called_once()
        storage.set_ondeck.assert_not_called()


# ── _process_sync_pending_shows ─────────────────────────────────────────

class TestProcessSyncPendingShows:
    """Tests for the instant clone handoff flag mechanism."""

    def test_noop_when_sync_disabled(self):
        """Should do nothing when multi-instance sync is off."""
        daemon = _make_daemon()
        daemon._sync_enabled = False
        daemon._window.getProperty.return_value = "131,438"

        daemon._process_sync_pending_shows()

        # Should not even read the property when sync is off
        daemon._window.getProperty.assert_not_called()

    def test_noop_when_flag_empty(self):
        """Should return immediately when flag property is empty."""
        daemon = _make_daemon()
        daemon._window.getProperty.return_value = ''

        daemon._process_sync_pending_shows()

        daemon._window.clearProperty.assert_not_called()

    def test_clears_flag_immediately(self):
        """Should clear the flag before processing."""
        daemon = _make_daemon()
        daemon._window.getProperty.return_value = '131,438'

        with patch.object(daemon, 'refresh_show_episodes'):
            daemon._process_sync_pending_shows()

        daemon._window.clearProperty.assert_called_once_with(PROP_SYNC_PENDING_SHOWS)

    def test_processes_new_shows(self):
        """Should call refresh_show_episodes for shows not already tracked."""
        daemon = _make_daemon()
        daemon._state.shows_with_next_episodes = [10, 20]
        daemon._window.getProperty.return_value = '131,438'

        with patch.object(daemon, 'refresh_show_episodes') as mock_refresh:
            daemon._process_sync_pending_shows()

        mock_refresh.assert_called_once()
        called_ids = set(mock_refresh.call_args[1]['showids'])
        assert called_ids == {131, 438}
        assert mock_refresh.call_args[1]['bulk'] is False

    def test_skips_already_tracked_shows(self):
        """Should not process shows already in daemon state."""
        daemon = _make_daemon()
        daemon._state.shows_with_next_episodes = [10, 131]
        daemon._window.getProperty.return_value = '131,438'

        with patch.object(daemon, 'refresh_show_episodes') as mock_refresh:
            daemon._process_sync_pending_shows()

        called_ids = set(mock_refresh.call_args[1]['showids'])
        assert called_ids == {438}

    def test_noop_when_all_already_tracked(self):
        """Should not call refresh when all flagged shows are already tracked."""
        daemon = _make_daemon()
        daemon._state.shows_with_next_episodes = [131, 438]
        daemon._window.getProperty.return_value = '131,438'

        with patch.object(daemon, 'refresh_show_episodes') as mock_refresh:
            daemon._process_sync_pending_shows()

        mock_refresh.assert_not_called()

    def test_handles_malformed_flag(self):
        """Should handle non-numeric entries in the flag gracefully."""
        daemon = _make_daemon()
        daemon._window.getProperty.return_value = '131,bad,438'

        with patch.object(daemon, 'refresh_show_episodes') as mock_refresh:
            daemon._process_sync_pending_shows()

        called_ids = set(mock_refresh.call_args[1]['showids'])
        assert called_ids == {131, 438}


# ── _initialize_storage (watermark seeding) ─────────────────────────────

class TestInitializeStorageWatermark:
    """Startup must seed the change-detection watermark."""

    @patch('resources.lib.service.daemon.get_storage')
    def test_seeds_watermark_from_max_updated_at(self, mock_get_storage):
        daemon = _make_daemon()
        storage = MagicMock(spec=SharedDatabaseStorage)
        storage.db = MagicMock()
        storage.db.is_empty.return_value = False
        storage.db.get_max_updated_at.return_value = "2026-06-23 22:00:00"
        mock_get_storage.return_value = storage

        with patch.object(daemon, '_validate_storage_ids'):
            daemon._initialize_storage()

        assert daemon._last_sync_updated_at == "2026-06-23 22:00:00"
