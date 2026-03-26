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
