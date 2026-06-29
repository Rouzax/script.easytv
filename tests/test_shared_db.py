"""Tests for resources/lib/data/shared_db.py — get_tracked_show_ids."""
import sys
from unittest.mock import MagicMock, patch

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


class TestGetMaxUpdatedAt:
    """Tests for SharedDatabase.get_max_updated_at()."""

    def test_returns_max_value(self):
        db, mock_conn = _make_shared_db()
        cur = MagicMock()
        mock_conn.cursor.return_value = cur
        cur.fetchone.return_value = ("2026-06-23 22:00:00",)

        assert db.get_max_updated_at() == "2026-06-23 22:00:00"
        cur.close.assert_called_once()

    def test_empty_table_returns_none(self):
        db, mock_conn = _make_shared_db()
        cur = MagicMock()
        mock_conn.cursor.return_value = cur
        cur.fetchone.return_value = (None,)

        assert db.get_max_updated_at() is None


class TestGetShowIdsUpdatedSince:
    """Tests for SharedDatabase.get_show_ids_updated_since()."""

    def test_returns_changed_ids_and_max_watermark(self):
        db, mock_conn = _make_shared_db()
        cur = MagicMock()
        mock_conn.cursor.return_value = cur
        cur.fetchall.return_value = [
            (101, "2026-06-23 21:00:00"),
            (202, "2026-06-23 21:05:00"),
        ]

        ids, watermark = db.get_show_ids_updated_since("2026-06-23 20:00:00")

        assert ids == {101, 202}
        assert watermark == "2026-06-23 21:05:00"
        cur.close.assert_called_once()

    def test_no_rows_keeps_since_watermark(self):
        db, mock_conn = _make_shared_db()
        cur = MagicMock()
        mock_conn.cursor.return_value = cur
        cur.fetchall.return_value = []

        ids, watermark = db.get_show_ids_updated_since("2026-06-23 20:00:00")

        assert ids == set()
        assert watermark == "2026-06-23 20:00:00"

    def test_none_since_returns_baseline_and_no_ids(self):
        db, _mock_conn = _make_shared_db()
        db.get_max_updated_at = MagicMock(return_value="2026-06-23 22:00:00")

        ids, watermark = db.get_show_ids_updated_since(None)

        assert ids == set()
        assert watermark == "2026-06-23 22:00:00"
        db.get_max_updated_at.assert_called_once()

    def test_uses_prefixed_table_and_idx_query(self):
        db, mock_conn = _make_shared_db(table_prefix="myp_")
        cur = MagicMock()
        mock_conn.cursor.return_value = cur
        cur.fetchall.return_value = [(1, "2026-06-23 21:00:00")]

        db.get_show_ids_updated_since("2026-06-23 20:00:00")

        sql = cur.execute.call_args[0][0]
        assert "myp_show_tracking" in sql
        assert "updated_at >= %s" in sql


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


class TestIsAvailableDoesNotMutateAdvertisedConfig:
    """
    Regression: clones share window properties with the main service.
    is_available() must never clear PROP_SHARED_DB_NAME / PROP_SHARED_DB_TABLE_PREFIX
    on connection failure; those are owned by the main service, and clearing them
    from a clone process permanently disables sync until the main service restarts.
    See RCA dated 2026-04-07.
    """

    @pytest.fixture(autouse=True)
    def _reset_backoff(self):
        """Reset class-level backoff state so tests don't bleed into each other."""
        from resources.lib.data.shared_db import SharedDatabase
        SharedDatabase._last_failure_time = 0
        SharedDatabase._backoff_notified = False
        yield
        SharedDatabase._last_failure_time = 0
        SharedDatabase._backoff_notified = False

    def test_pymysql_import_error_does_not_clear_advertised_config(self, mocker):
        """Real ImportError path: clone tries to connect, pymysql missing, advertisement preserved."""
        import sys

        from resources.lib.constants import (
            PROP_SHARED_DB_NAME,
            PROP_SHARED_DB_TABLE_PREFIX,
        )
        from resources.lib.data import shared_db as shared_db_mod
        from resources.lib.data.shared_db import SharedDatabase

        # Capture clearProperty calls; getProperty is unused on the failure path
        mock_window = mocker.patch.object(shared_db_mod, 'WINDOW')
        cleared_keys = []
        mock_window.clearProperty.side_effect = lambda key: cleared_keys.append(key)

        # Force a real ImportError on `import pymysql` inside _connect()
        saved = sys.modules.get('pymysql', 'NOT_PRESENT')
        sys.modules['pymysql'] = None
        try:
            db = SharedDatabase()
            db._easytv_db_name = 'easytv_mastervideo'
            db._table_prefix = ''
            result = db.is_available()
        finally:
            if saved == 'NOT_PRESENT':
                sys.modules.pop('pymysql', None)
            else:
                sys.modules['pymysql'] = saved

        assert result is False, "is_available should return False when pymysql missing"
        assert PROP_SHARED_DB_NAME not in cleared_keys, (
            "is_available must not clear PROP_SHARED_DB_NAME; it's owned by main service"
        )
        assert PROP_SHARED_DB_TABLE_PREFIX not in cleared_keys, (
            "is_available must not clear PROP_SHARED_DB_TABLE_PREFIX; it's owned by main service"
        )

    def test_pymysql_import_error_does_not_clear_sync_rev(self, mocker):
        """sync_rev is local cache state of the main service; clones must not clear it."""
        import sys

        from resources.lib.data import shared_db as shared_db_mod
        from resources.lib.data.shared_db import SharedDatabase

        mock_window = mocker.patch.object(shared_db_mod, 'WINDOW')
        cleared_keys = []
        mock_window.clearProperty.side_effect = lambda key: cleared_keys.append(key)

        saved = sys.modules.get('pymysql', 'NOT_PRESENT')
        sys.modules['pymysql'] = None
        try:
            db = SharedDatabase()
            db.is_available()
        finally:
            if saved == 'NOT_PRESENT':
                sys.modules.pop('pymysql', None)
            else:
                sys.modules['pymysql'] = saved

        assert "EasyTV.sync_rev" not in cleared_keys, (
            "is_available must not clear EasyTV.sync_rev; it's main-service-owned cache state"
        )


class TestGetShowTrackingBulkWithRev:
    """Tests for SharedDatabase.get_show_tracking_bulk_with_rev()."""

    def test_returns_updated_at_per_show(self):
        db, mock_conn = _make_shared_db()
        cur = MagicMock()
        mock_conn.cursor.return_value = cur
        cur.fetchall.return_value = [{
            'show_id': 42,
            'show_title': 'X',
            'show_year': 2020,
            'ondeck_episode_id': 100,
            'ondeck_list': '[100]',
            'offdeck_list': '[]',
            'watched_count': 1,
            'unwatched_count': 5,
            'updated_at': '2026-06-24 10:00:00',
            'current_rev': 7,
        }]

        # The method imports pymysql.cursors for a DictCursor; mock it so the
        # test runs without pymysql installed (e.g. CI), matching how the other
        # connection internals are mocked here.
        fake_pymysql = MagicMock()
        with patch.dict(
            sys.modules,
            {'pymysql': fake_pymysql, 'pymysql.cursors': fake_pymysql.cursors},
        ):
            data, rev = db.get_show_tracking_bulk_with_rev([42])

        assert rev == 7
        assert data[42]['updated_at'] == '2026-06-24 10:00:00'
        assert data[42]['ondeck_episode_id'] == 100


class TestDeleteBumpsRevision:
    """Tests that delete_show_tracking bumps global_rev when rows are deleted."""

    def test_bumps_global_rev_when_rows_deleted(self):
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.rowcount = 2
        db.delete_show_tracking([11, 12])

        sql_calls = " ".join(c.args[0] for c in mock_cursor.execute.call_args_list)
        assert "global_rev" in sql_calls

    def test_no_rev_bump_when_no_rows_deleted(self):
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.rowcount = 0
        db.delete_show_tracking([99])

        sql_calls = " ".join(c.args[0] for c in mock_cursor.execute.call_args_list)
        assert "global_rev" not in sql_calls

    def test_returns_deleted_count(self):
        db, mock_conn = _make_shared_db()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.rowcount = 3
        result = db.delete_show_tracking([1, 2, 3])

        assert result == 3
