"""Tests for resources/lib/data/storage.py."""
from unittest.mock import MagicMock, patch

import pytest

from resources.lib.data.storage import (
    SharedDatabaseStorage,
    SyncResult,
    WindowPropertyStorage,
    _build_property_key,
)


class TestWindowPropertyStorageGetTrackedShowIds:
    """Tests for WindowPropertyStorage.get_tracked_show_ids()."""

    def test_returns_empty_set_and_zero_revision(self):
        storage = WindowPropertyStorage()

        show_ids, revision = storage.get_tracked_show_ids()

        assert show_ids == set()
        assert revision == 0

    def test_return_types(self):
        storage = WindowPropertyStorage()

        show_ids, revision = storage.get_tracked_show_ids()

        assert isinstance(show_ids, set)
        assert isinstance(revision, int)


class TestSharedDatabaseStorageGetTrackedShowIds:
    """Tests for SharedDatabaseStorage.get_tracked_show_ids()."""

    def _make_storage(self):
        """Create a SharedDatabaseStorage with a mocked database."""
        mock_db = MagicMock()
        storage = SharedDatabaseStorage(mock_db)
        return storage, mock_db

    def test_delegates_to_db(self):
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = ({10, 20, 30}, 5)

        show_ids, revision = storage.get_tracked_show_ids()

        assert show_ids == {10, 20, 30}
        assert revision == 5
        mock_db.get_tracked_show_ids.assert_called_once()

    def test_empty_result_from_db(self):
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = (set(), 3)

        show_ids, revision = storage.get_tracked_show_ids()

        assert show_ids == set()
        assert revision == 3

    def test_propagates_db_exception(self):
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.side_effect = Exception("connection lost")

        with pytest.raises(Exception, match="connection lost"):
            storage.get_tracked_show_ids()


class TestRefreshResumeState:
    """Tests for SharedDatabaseStorage._refresh_resume_state()."""

    def _make_storage(self):
        """Create a SharedDatabaseStorage with a mocked database."""
        mock_db = MagicMock()
        storage = SharedDatabaseStorage(mock_db)
        return storage, mock_db

    @patch('resources.lib.data.storage.WINDOW')
    @patch('resources.lib.data.storage.json_query')
    def test_updates_resume_properties_when_episode_has_resume(
        self, mock_json_query, mock_window
    ):
        """Resume and PercentPlayed are set when episode has a resume point."""
        storage, _ = self._make_storage()
        mock_json_query.return_value = {
            'episodedetails': {
                'resume': {'position': 300.0, 'total': 1200.0}
            }
        }

        storage._refresh_resume_state(show_id=42, episode_id=100)

        resume_key = _build_property_key(42, "Resume")
        percent_key = _build_property_key(42, "PercentPlayed")
        mock_window.setProperty.assert_any_call(resume_key, "true")
        mock_window.setProperty.assert_any_call(percent_key, "25%")

    @patch('resources.lib.data.storage.WINDOW')
    @patch('resources.lib.data.storage.json_query')
    def test_sets_no_resume_when_position_is_zero(
        self, mock_json_query, mock_window
    ):
        """Resume is false and PercentPlayed is 0% when no resume data."""
        storage, _ = self._make_storage()
        mock_json_query.return_value = {
            'episodedetails': {
                'resume': {'position': 0, 'total': 0}
            }
        }

        storage._refresh_resume_state(show_id=42, episode_id=100)

        resume_key = _build_property_key(42, "Resume")
        percent_key = _build_property_key(42, "PercentPlayed")
        mock_window.setProperty.assert_any_call(resume_key, "false")
        mock_window.setProperty.assert_any_call(percent_key, "0%")

    @patch('resources.lib.data.storage.WINDOW')
    @patch('resources.lib.data.storage.json_query')
    def test_no_update_when_query_fails(
        self, mock_json_query, mock_window
    ):
        """Window properties are not touched when the Kodi query raises."""
        storage, _ = self._make_storage()
        mock_json_query.side_effect = Exception("JSON-RPC timeout")

        storage._refresh_resume_state(show_id=42, episode_id=100)

        mock_window.setProperty.assert_not_called()

    @patch('resources.lib.data.storage.WINDOW')
    @patch('resources.lib.data.storage.json_query')
    def test_no_update_when_episodedetails_missing(
        self, mock_json_query, mock_window
    ):
        """Window properties are not touched when response lacks episodedetails."""
        storage, _ = self._make_storage()
        mock_json_query.return_value = {}

        storage._refresh_resume_state(show_id=42, episode_id=100)

        mock_window.setProperty.assert_not_called()

    @patch('resources.lib.data.storage.WINDOW')
    @patch('resources.lib.data.storage.json_query')
    def test_sets_no_resume_when_resume_dict_missing(
        self, mock_json_query, mock_window
    ):
        """Resume is false when episodedetails has no resume key."""
        storage, _ = self._make_storage()
        mock_json_query.return_value = {
            'episodedetails': {}
        }

        storage._refresh_resume_state(show_id=42, episode_id=100)

        resume_key = _build_property_key(42, "Resume")
        percent_key = _build_property_key(42, "PercentPlayed")
        mock_window.setProperty.assert_any_call(resume_key, "false")
        mock_window.setProperty.assert_any_call(percent_key, "0%")


class TestWindowPropertyStorageSyncTrackedShows:
    """Tests for WindowPropertyStorage.sync_tracked_shows()."""

    def test_returns_empty_sync_result(self):
        storage = WindowPropertyStorage()

        result = storage.sync_tracked_shows({1, 2, 3})

        assert result.added == set()
        assert result.removed == set()
        assert result.revision == 0

    def test_returns_sync_result_type(self):
        storage = WindowPropertyStorage()

        result = storage.sync_tracked_shows(set())

        assert isinstance(result, SyncResult)


class TestSharedDatabaseStorageSyncTrackedShows:
    """Tests for SharedDatabaseStorage.sync_tracked_shows()."""

    def _make_storage(self):
        """Create a SharedDatabaseStorage with a mocked database."""
        mock_db = MagicMock()
        storage = SharedDatabaseStorage(mock_db)
        return storage, mock_db

    def test_discovers_additions(self):
        """Shows in DB but not local are reported as added."""
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = ({10, 20, 30}, 5)

        result = storage.sync_tracked_shows({10, 20})

        assert result.added == {30}
        assert result.removed == set()
        assert result.revision == 5

    def test_discovers_removals(self):
        """Shows in local but not DB are reported as removed."""
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = ({10}, 7)

        result = storage.sync_tracked_shows({10, 20, 30})

        assert result.added == set()
        assert result.removed == {20, 30}
        assert result.revision == 7

    def test_no_changes(self):
        """No additions or removals when sets match."""
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = ({10, 20, 30}, 3)

        result = storage.sync_tracked_shows({10, 20, 30})

        assert result.added == set()
        assert result.removed == set()
        assert result.revision == 3

    def test_both_additions_and_removals(self):
        """Both additions and removals detected simultaneously."""
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = ({10, 40, 50}, 9)

        result = storage.sync_tracked_shows({10, 20, 30})

        assert result.added == {40, 50}
        assert result.removed == {20, 30}
        assert result.revision == 9

    def test_empty_db_all_removed(self):
        """All local shows reported as removed when DB is empty."""
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = (set(), 2)

        result = storage.sync_tracked_shows({10, 20})

        assert result.added == set()
        assert result.removed == {10, 20}
        assert result.revision == 2

    def test_empty_local_all_added(self):
        """All DB shows reported as added when local is empty."""
        storage, mock_db = self._make_storage()
        mock_db.get_tracked_show_ids.return_value = ({10, 20}, 4)

        result = storage.sync_tracked_shows(set())

        assert result.added == {10, 20}
        assert result.removed == set()
        assert result.revision == 4


class TestGetStorageCloneFallback:
    """Test get_storage() clone fallback via advertised shared DB config."""

    def setup_method(self):
        """Reset storage singleton before each test."""
        from resources.lib.data.storage import reset_storage
        reset_storage()

    def test_clone_uses_window_property_when_no_advertised_config(self, mocker):
        """Clone without advertised DB config falls back to WindowPropertyStorage."""
        from resources.lib.data import storage as storage_mod
        from resources.lib.data.storage import get_storage, WindowPropertyStorage

        mocker.patch.object(storage_mod, 'get_bool_setting', return_value=False)
        mock_window = mocker.patch.object(storage_mod, 'WINDOW')
        mock_window.getProperty.return_value = ''

        result = get_storage()
        assert isinstance(result, WindowPropertyStorage)

    def test_clone_uses_shared_db_when_advertised(self, mocker):
        """Clone with advertised DB config creates SharedDatabaseStorage."""
        from resources.lib.data import storage as storage_mod
        from resources.lib.data.storage import get_storage, SharedDatabaseStorage

        mocker.patch.object(storage_mod, 'get_bool_setting', return_value=False)

        def fake_get_prop(key):
            from resources.lib.constants import PROP_SHARED_DB_NAME, PROP_SHARED_DB_TABLE_PREFIX
            props = {
                PROP_SHARED_DB_NAME: 'easytv_mastervideo',
                PROP_SHARED_DB_TABLE_PREFIX: '',
            }
            return props.get(key, '')
        mock_window = mocker.patch.object(storage_mod, 'WINDOW')
        mock_window.getProperty.side_effect = fake_get_prop

        mock_db_class = mocker.patch(
            'resources.lib.data.shared_db.SharedDatabase'
        )
        mock_db_instance = mock_db_class.return_value
        mock_db_instance.is_available.return_value = True

        result = get_storage()
        assert isinstance(result, SharedDatabaseStorage)

    def test_clone_falls_back_when_advertised_db_unavailable(self, mocker):
        """Clone falls back if advertised DB is unreachable."""
        from resources.lib.data import storage as storage_mod
        from resources.lib.data.storage import get_storage, WindowPropertyStorage

        mocker.patch.object(storage_mod, 'get_bool_setting', return_value=False)

        def fake_get_prop(key):
            from resources.lib.constants import PROP_SHARED_DB_NAME, PROP_SHARED_DB_TABLE_PREFIX
            props = {
                PROP_SHARED_DB_NAME: 'easytv_mastervideo',
                PROP_SHARED_DB_TABLE_PREFIX: '',
            }
            return props.get(key, '')
        mock_window = mocker.patch.object(storage_mod, 'WINDOW')
        mock_window.getProperty.side_effect = fake_get_prop

        mock_db_class = mocker.patch(
            'resources.lib.data.shared_db.SharedDatabase'
        )
        mock_db_instance = mock_db_class.return_value
        mock_db_instance.is_available.return_value = False

        result = get_storage()
        assert isinstance(result, WindowPropertyStorage)

    def test_clone_falls_back_when_pymysql_import_fails(self, mocker):
        """
        Real ImportError path: clone reads valid advertisement but pymysql is missing.
        Verifies fallback to WindowPropertyStorage AND that the advertisement is
        preserved (regression for the 2026-04-07 RCA).
        """
        import sys
        from resources.lib.constants import (
            PROP_SHARED_DB_NAME,
            PROP_SHARED_DB_TABLE_PREFIX,
        )
        from resources.lib.data import storage as storage_mod
        from resources.lib.data.storage import (
            get_storage,
            reset_storage,
            WindowPropertyStorage,
        )
        from resources.lib.data import shared_db as shared_db_mod
        from resources.lib.data.shared_db import SharedDatabase

        # Reset class-level backoff state and storage singleton
        SharedDatabase._last_failure_time = 0
        SharedDatabase._backoff_notified = False
        reset_storage()

        mocker.patch.object(storage_mod, 'get_bool_setting', return_value=False)

        stored_props = {
            PROP_SHARED_DB_NAME: 'easytv_mastervideo',
            PROP_SHARED_DB_TABLE_PREFIX: '',
        }
        cleared_keys = []

        def fake_get(key):
            return stored_props.get(key, '')

        # Patch WINDOW in BOTH modules; storage.py and shared_db.py both hold
        # separate module-level references to xbmcgui.Window(10000).
        for mod in (storage_mod, shared_db_mod):
            mock_window = mocker.patch.object(mod, 'WINDOW')
            mock_window.getProperty.side_effect = fake_get
            mock_window.clearProperty.side_effect = lambda key: cleared_keys.append(key)

        # Force ImportError on `import pymysql` inside SharedDatabase._connect()
        saved = sys.modules.get('pymysql', 'NOT_PRESENT')
        sys.modules['pymysql'] = None
        try:
            result = get_storage()
        finally:
            if saved == 'NOT_PRESENT':
                sys.modules.pop('pymysql', None)
            else:
                sys.modules['pymysql'] = saved
            reset_storage()
            SharedDatabase._last_failure_time = 0
            SharedDatabase._backoff_notified = False

        assert isinstance(result, WindowPropertyStorage), (
            "Clone must fall back to WindowPropertyStorage on pymysql ImportError"
        )
        assert PROP_SHARED_DB_NAME not in cleared_keys, (
            "Clone must not clear PROP_SHARED_DB_NAME; owned by main service"
        )
        assert PROP_SHARED_DB_TABLE_PREFIX not in cleared_keys, (
            "Clone must not clear PROP_SHARED_DB_TABLE_PREFIX; owned by main service"
        )
