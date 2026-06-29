"""Tests for ServiceDaemon producer drop-and-delete logic in refresh_show_episodes."""
from typing import List
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def make_daemon():
    """Build a minimal ServiceDaemon for testing refresh_show_episodes.

    Constructs the daemon via object.__new__ so no Kodi runtime is required.
    Only the attributes touched by refresh_show_episodes are populated.

    Args:
        tracked: Initial value for _state.shows_with_next_episodes.
        random_order: Value for _settings.random_order_shows.
    """
    from resources.lib.service.daemon import ServiceDaemon

    def _make(tracked: List[int], random_order: List[int]) -> ServiceDaemon:
        daemon = object.__new__(ServiceDaemon)
        daemon._log = MagicMock()
        daemon._window = MagicMock()
        daemon._episode_tracker = MagicMock()

        settings = MagicMock()
        settings.random_order_shows = random_order
        # Disable playlist exports so start_playlist_batch is never called.
        settings.playlist_export_episodes = False
        settings.playlist_export_tvshows = False
        settings.include_positioned_specials = False
        settings.smartplaylist_filter_enabled = False
        daemon._settings = settings

        class _State:
            shows_with_next_episodes: List[int]

        state = _State()
        state.shows_with_next_episodes = list(tracked)
        daemon._state = state

        return daemon

    return _make


# ---------------------------------------------------------------------------
# TestProducerDropAndDelete
# ---------------------------------------------------------------------------

class TestProducerDropAndDelete:
    """refresh_show_episodes removes and deletes fully-watched shows."""

    def test_bulk_drops_and_deletes_fully_watched(self, mocker, make_daemon):
        """Bulk mode: show 11 is fully watched; must be removed locally and deleted in DB."""
        d = make_daemon(tracked=[11, 12], random_order=[])
        # json_query returns only show 12 as playcount=0 (show 11 is fully watched).
        # The response has no 'episodes' key so episodes_by_show stays empty,
        # which causes the inner loop to skip episode processing (eps=[]).
        mocker.patch(
            "resources.lib.service.daemon.json_query",
            return_value={"tvshows": [{"tvshowid": 12, "year": 0}]},
        )
        mocker.patch(
            "resources.lib.service.daemon.query_unwatched_show_ids",
            return_value={12},
        )
        storage = mocker.MagicMock()
        mocker.patch("resources.lib.service.daemon.get_storage", return_value=storage)
        mocker.patch("resources.lib.service.daemon.is_shared_storage", return_value=True)
        remove = mocker.patch.object(d, "_remove_from_shows_with_next_episodes")

        d.refresh_show_episodes(showids=[12], bulk=True)

        remove.assert_any_call(11)
        storage.db.delete_show_tracking.assert_called_once()
        assert set(storage.db.delete_show_tracking.call_args.args[0]) == {11}

    def test_eject_offdeck_show_row_not_deleted(self, mocker, make_daemon):
        """A show with offdeck-only unwatched episodes stays in the unwatched set.

        Such a show is playcount=0 so it appears in query_unwatched_show_ids,
        and must NOT be deleted from the shared DB by the bulk producer.
        """
        d = make_daemon(tracked=[11], random_order=[])
        mocker.patch(
            "resources.lib.service.daemon.json_query",
            return_value={"tvshows": [{"tvshowid": 11, "year": 0}]},
        )
        mocker.patch(
            "resources.lib.service.daemon.query_unwatched_show_ids",
            return_value={11},
        )
        storage = mocker.MagicMock()
        mocker.patch("resources.lib.service.daemon.get_storage", return_value=storage)
        mocker.patch("resources.lib.service.daemon.is_shared_storage", return_value=True)

        d.refresh_show_episodes(showids=[11], bulk=True)

        storage.db.delete_show_tracking.assert_not_called()

    def test_sync_off_no_db_delete_no_crash(self, mocker, make_daemon):
        """Local (non-shared) storage: local removal still happens, no DB delete called."""
        d = make_daemon(tracked=[11, 12], random_order=[])
        mocker.patch(
            "resources.lib.service.daemon.json_query",
            return_value={"tvshows": [{"tvshowid": 12, "year": 0}]},
        )
        mocker.patch(
            "resources.lib.service.daemon.query_unwatched_show_ids",
            return_value={12},
        )
        # Plain MagicMock (no spec): simulates any storage backend that lacks .db.
        # The guard `if to_delete and is_shared_storage():` prevents the .db access.
        storage = mocker.MagicMock()
        mocker.patch("resources.lib.service.daemon.get_storage", return_value=storage)
        mocker.patch("resources.lib.service.daemon.is_shared_storage", return_value=False)
        remove = mocker.patch.object(d, "_remove_from_shows_with_next_episodes")

        d.refresh_show_episodes(showids=[12], bulk=True)  # must not raise

        remove.assert_any_call(11)
        storage.db.delete_show_tracking.assert_not_called()
