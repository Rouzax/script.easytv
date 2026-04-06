"""Tests for resources/lib/data/shared_db.py — get_tracked_show_ids."""
from unittest.mock import MagicMock

import pytest


def _make_shared_db(table_prefix="etv_"):
    """Create a SharedDatabase instance with mocked internals."""
    from resources.lib.data.shared_db import SharedDatabase
    db = SharedDatabase.__new__(SharedDatabase)
    mock_conn = MagicMock()
    db._conn = mock_conn
    db._table_prefix = table_prefix
    # _get_connection returns _conn after ping/reconnect; we shortcut it
    db._get_connection = MagicMock(return_value=mock_conn)

    return db, mock_conn


class TestGetTrackedShowIds:
    """Tests for SharedDatabase.get_tracked_show_ids()."""

    def test_returns_show_ids_and_revision(self):
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (101, 5),
            (202, 5),
            (303, 5),
        ]

        show_ids, revision = db.get_tracked_show_ids()

        assert show_ids == {101, 202, 303}
        assert revision == 5
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_empty_table_returns_empty_set(self):
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        # Mock get_global_rev for the fallback path
        db.get_global_rev = MagicMock(return_value=7)

        show_ids, revision = db.get_tracked_show_ids()

        assert show_ids == set()
        assert revision == 7
        db.get_global_rev.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_single_show(self):
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(42, 3)]

        show_ids, revision = db.get_tracked_show_ids()

        assert show_ids == {42}
        assert revision == 3

    def test_revision_taken_from_first_row(self):
        """All rows have the same revision via CROSS JOIN; we take row[0][1]."""
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (1, 10),
            (2, 10),
        ]

        _, revision = db.get_tracked_show_ids()
        assert revision == 10

    def test_uses_correct_table_names(self):
        db, mock_conn = _make_shared_db(table_prefix="myprefix_")
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, 1)]

        db.get_tracked_show_ids()

        sql = mock_cursor.execute.call_args[0][0]
        assert 'myprefix_show_tracking' in sql
        assert 'myprefix_sync_metadata' in sql

    def test_cursor_closed_on_exception(self):
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            db.get_tracked_show_ids()

        mock_cursor.close.assert_called_once()


class TestValidateAndMigrateIds:
    """Tests for SharedDatabase.validate_and_migrate_ids()."""

    def test_valid_show_unchanged(self):
        """Show with matching ID + title is counted as valid."""
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # get_all_stored_shows returns one show
        db.get_all_stored_shows = MagicMock(return_value={
            100: ("Breaking Bad", 2008),
        })

        current_shows = {100: ("Breaking Bad", 2008)}

        migrated, orphaned, valid = db.validate_and_migrate_ids(current_shows)

        assert valid == 1
        assert migrated == 0
        assert orphaned == 0

    def test_stale_entry_deleted_when_target_already_exists(self):
        """Stale entry whose title+year matches an already-valid row is deleted, not migrated."""
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # DB has two rows for same show: stale 186 and valid 430
        db.get_all_stored_shows = MagicMock(return_value={
            186: ("ONE PIECE", 2023),
            430: ("ONE PIECE", 2023),
        })
        db.delete_show_tracking = MagicMock(return_value=1)
        db.migrate_show_id = MagicMock(return_value=True)

        # Current library only has show 430
        current_shows = {430: ("ONE PIECE", 2023)}

        migrated, orphaned, valid = db.validate_and_migrate_ids(current_shows)

        assert valid == 1      # show 430 is valid
        assert orphaned == 1   # show 186 is orphaned
        assert migrated == 0   # no migration attempted
        # migrate_show_id must NOT be called (would cause duplicate key)
        db.migrate_show_id.assert_not_called()
        # 186 should be in the deleted orphans
        db.delete_show_tracking.assert_called_once()
        deleted_ids = db.delete_show_tracking.call_args[0][0]
        assert 186 in deleted_ids

    def test_legitimate_migration_still_works(self):
        """Show whose ID shifted (no existing row at target) migrates normally."""
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # DB has show 50 ("The Office", 2005) but library now has it at 75
        db.get_all_stored_shows = MagicMock(return_value={
            50: ("The Office", 2005),
        })
        db.migrate_show_id = MagicMock(return_value=True)
        db.delete_show_tracking = MagicMock(return_value=0)

        current_shows = {75: ("The Office", 2005)}

        migrated, orphaned, valid = db.validate_and_migrate_ids(current_shows)

        assert migrated == 1
        assert orphaned == 0
        assert valid == 0
        db.migrate_show_id.assert_called_once_with(50, 75, clear_episode_lists=True)
