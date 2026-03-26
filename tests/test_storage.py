"""Tests for resources/lib/data/storage.py — get_tracked_show_ids."""
from unittest.mock import MagicMock

import pytest

from resources.lib.data.storage import (
    SharedDatabaseStorage,
    WindowPropertyStorage,
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
