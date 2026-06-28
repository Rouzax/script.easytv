"""Tests for resources/lib/data/shows.py — show data logic."""
import random
from unittest.mock import MagicMock, patch

from resources.lib.constants import (
    CATEGORY_CONTINUE_WATCHING,
    CATEGORY_SEASON_PREMIERE,
    CATEGORY_SHOW_PREMIERE,
    CATEGORY_START_FRESH,
    PROP_SHOWS_WITH_NEXT_EPISODES,
    PROP_SYNC_PENDING_SHOWS,
)
from resources.lib.data.shows import (
    _get_playlist_filename,
    fetch_shows_with_watched_episodes,
    generate_sort_key,
    get_episode_sort_key,
    get_premiere_category,
    get_show_category,
    parse_season_episode_string,
    resolve_ondeck_episode,
    sync_show_list_from_shared_db,
)
from resources.lib.data.storage import SyncResult

# ── generate_sort_key ────────────────────────────────────────────────

class TestGenerateSortKey:
    def test_english_the(self):
        assert generate_sort_key("The Office", "English") == "office"

    def test_english_a(self):
        assert generate_sort_key("A Man Apart", "English") == "man apart"

    def test_german_der(self):
        assert generate_sort_key("Der Alte", "German") == "alte"

    def test_dutch_de(self):
        assert generate_sort_key("De Mol", "Dutch") == "mol"

    def test_spanish_el(self):
        assert generate_sort_key("El Camino", "Spanish") == "camino"

    def test_no_article_passthrough(self):
        assert generate_sort_key("Breaking Bad", "English") == "breaking bad"

    def test_compound_language(self):
        assert generate_sort_key("The Office", "English (US)") == "office"

    def test_case_insensitive(self):
        assert generate_sort_key("THE OFFICE", "English") == "office"

    def test_unknown_language(self):
        assert generate_sort_key("The Office", "Klingon") == "the office"


# ── parse_season_episode_string ──────────────────────────────────────

class TestParseSeasonEpisodeString:
    def test_single_digit_int(self):
        assert parse_season_episode_string(1) == "01"

    def test_double_digit_int(self):
        assert parse_season_episode_string(12) == "12"

    def test_string_input(self):
        assert parse_season_episode_string("5") == "05"

    def test_zero(self):
        assert parse_season_episode_string(0) == "00"

    def test_large_number(self):
        assert parse_season_episode_string(100) == "100"


# ── get_episode_sort_key ─────────────────────────────────────────────

class TestGetEpisodeSortKey:
    def test_regular_episode(self):
        ep = {'season': 3, 'episode': 5}
        assert get_episode_sort_key(ep) == (3, 5, 0, 5)

    def test_positioned_special(self):
        ep = {'season': 0, 'episode': 5, 'specialsortseason': 3, 'specialsortepisode': 10}
        key = get_episode_sort_key(ep, include_positioned_specials=True)
        assert key == (3, 10, -1, 5)

    def test_non_positioned_special(self):
        ep = {'season': 0, 'episode': 20, 'specialsortseason': -1, 'specialsortepisode': -1}
        key = get_episode_sort_key(ep, include_positioned_specials=True)
        assert key == (0, 20, 0, 20)

    def test_specials_disabled(self):
        ep = {'season': 0, 'episode': 5, 'specialsortseason': 3, 'specialsortepisode': 10}
        key = get_episode_sort_key(ep, include_positioned_specials=False)
        assert key == (0, 5, 0, 5)

    def test_special_sorts_before_target(self):
        regular = get_episode_sort_key(
            {'season': 3, 'episode': 10}, include_positioned_specials=True
        )
        special = get_episode_sort_key(
            {'season': 0, 'episode': 5, 'specialsortseason': 3, 'specialsortepisode': 10},
            include_positioned_specials=True
        )
        assert special < regular


# ── get_show_category ────────────────────────────────────────────────

class TestGetShowCategory:
    def test_episode_1_is_start_fresh(self):
        assert get_show_category(1) == CATEGORY_START_FRESH

    def test_episode_2_is_continue(self):
        assert get_show_category(2) == CATEGORY_CONTINUE_WATCHING

    def test_episode_10_is_continue(self):
        assert get_show_category(10) == CATEGORY_CONTINUE_WATCHING

    def test_episode_1_with_resume_is_continue(self):
        """Partially-watched premiere should be continue_watching, not start_fresh."""
        assert get_show_category(1, has_resume=True) == CATEGORY_CONTINUE_WATCHING

    def test_episode_1_without_resume_is_start_fresh(self):
        assert get_show_category(1, has_resume=False) == CATEGORY_START_FRESH

    def test_episode_2_with_resume_is_continue(self):
        assert get_show_category(2, has_resume=True) == CATEGORY_CONTINUE_WATCHING


# ── get_premiere_category ────────────────────────────────────────────

class TestGetPremiereCategory:
    def test_s01e01_show_premiere(self):
        assert get_premiere_category(1, 1) == CATEGORY_SHOW_PREMIERE

    def test_s02e01_season_premiere(self):
        assert get_premiere_category(2, 1) == CATEGORY_SEASON_PREMIERE

    def test_s05e01_season_premiere(self):
        assert get_premiere_category(5, 1) == CATEGORY_SEASON_PREMIERE

    def test_s01e02_not_premiere(self):
        assert get_premiere_category(1, 2) == ""

    def test_s03e05_not_premiere(self):
        assert get_premiere_category(3, 5) == ""

    def test_s01e01_with_resume_not_premiere(self):
        """Partially-watched show premiere is no longer a premiere."""
        assert get_premiere_category(1, 1, has_resume=True) == ""

    def test_s02e01_with_resume_not_premiere(self):
        """Partially-watched season premiere is no longer a premiere."""
        assert get_premiere_category(2, 1, has_resume=True) == ""

    def test_s05e01_with_resume_not_premiere(self):
        assert get_premiere_category(5, 1, has_resume=True) == ""


# ── _get_playlist_filename ───────────────────────────────────────────

class TestGetPlaylistFilename:
    def test_plugin_url_returns_full_path(self):
        url = "plugin://plugin.video.jellyfin/some/path"
        assert _get_playlist_filename(url) == url

    def test_local_path_returns_basename(self):
        assert _get_playlist_filename("/media/TV/Show/episode.mkv") == "episode.mkv"

    def test_windows_path(self):
        # os.path.basename handles platform-specific separators
        result = _get_playlist_filename("/some/path/file.avi")
        assert result == "file.avi"


# ── resolve_ondeck_episode ──────────────────────────────────────────

class TestResolveOndeckEpisode:
    def test_sequential_prefers_first_ondeck(self):
        assert resolve_ondeck_episode([10, 11, 12], [3, 4], False) == 10

    def test_sequential_falls_back_to_offdeck_when_no_ondeck(self):
        assert resolve_ondeck_episode([], [3, 4], False) == 3

    def test_random_pick_is_from_pool(self):
        random.seed(1)
        pool = {10, 11, 12, 3, 4}
        for _ in range(20):
            assert resolve_ondeck_episode([10, 11, 12], [3, 4], True) in pool

    def test_empty_pool_returns_none(self):
        assert resolve_ondeck_episode([], [], True) is None
        assert resolve_ondeck_episode([], [], False) is None


# ── sync_show_list_from_shared_db ──────────────────────────────────

class TestSyncShowListFromSharedDb:
    """Tests for sync_show_list_from_shared_db()."""

    def _make_storage(self):
        """Create a mock storage backend."""
        return MagicMock()

    def _make_logger(self):
        """Create a mock logger."""
        logger = MagicMock()
        return logger

    @patch('resources.lib.data.shows.WINDOW')
    def test_noop_when_no_shows_property(self, mock_window):
        """Should return early if PROP_SHOWS_WITH_NEXT_EPISODES is empty."""
        mock_window.getProperty.return_value = ''
        storage = self._make_storage()

        sync_show_list_from_shared_db(storage)

        storage.sync_tracked_shows.assert_not_called()

    @patch('resources.lib.data.shows.WINDOW')
    def test_noop_when_nothing_changed(self, mock_window):
        """Should not update property when sync_tracked_shows reports no changes."""
        mock_window.getProperty.return_value = '[10, 20, 30]'
        storage = self._make_storage()
        storage.sync_tracked_shows.return_value = SyncResult(
            added=set(), removed=set(), revision=5
        )

        sync_show_list_from_shared_db(storage)

        mock_window.setProperty.assert_not_called()

    @patch('resources.lib.data.shows.WINDOW')
    def test_adds_shows_from_shared_db(self, mock_window):
        """Should add new shows discovered in shared DB."""
        mock_window.getProperty.return_value = '[10, 20]'
        storage = self._make_storage()
        storage.sync_tracked_shows.return_value = SyncResult(
            added={30, 40}, removed=set(), revision=5
        )
        # get_ondeck_bulk returns data for both added shows
        storage.get_ondeck_bulk.return_value = ({30: {}, 40: {}}, 5)
        logger = self._make_logger()

        sync_show_list_from_shared_db(storage, logger)

        storage.get_ondeck_bulk.assert_called_once_with(
            list({30, 40}), refresh_display=True
        )
        # Verify property was updated with all 4 shows
        call_args = mock_window.setProperty.call_args
        assert call_args[0][0] == PROP_SHOWS_WITH_NEXT_EPISODES
        updated_ids = eval(call_args[0][1])
        assert set(updated_ids) == {10, 20, 30, 40}

    @patch('resources.lib.data.shows.WINDOW')
    def test_sets_pending_flag_on_add(self, mock_window):
        """Should set PROP_SYNC_PENDING_SHOWS with added show IDs."""
        mock_window.getProperty.return_value = '[10, 20]'
        storage = self._make_storage()
        storage.sync_tracked_shows.return_value = SyncResult(
            added={30, 40}, removed=set(), revision=5
        )
        storage.get_ondeck_bulk.return_value = ({30: {}, 40: {}}, 5)
        logger = self._make_logger()

        sync_show_list_from_shared_db(storage, logger)

        # Find the setProperty call for the pending flag
        pending_calls = [
            c for c in mock_window.setProperty.call_args_list
            if c[0][0] == PROP_SYNC_PENDING_SHOWS
        ]
        assert len(pending_calls) == 1
        flag_value = pending_calls[0][0][1]
        flag_ids = {int(x) for x in flag_value.split(',')}
        assert flag_ids == {30, 40}

    @patch('resources.lib.data.shows.WINDOW')
    def test_removes_shows_from_shared_db(self, mock_window):
        """Should remove shows no longer in shared DB."""
        mock_window.getProperty.return_value = '[10, 20, 30]'
        storage = self._make_storage()
        storage.sync_tracked_shows.return_value = SyncResult(
            added=set(), removed={30}, revision=5
        )
        logger = self._make_logger()

        sync_show_list_from_shared_db(storage, logger)

        call_args = mock_window.setProperty.call_args
        assert call_args[0][0] == PROP_SHOWS_WITH_NEXT_EPISODES
        updated_ids = eval(call_args[0][1])
        assert set(updated_ids) == {10, 20}

    @patch('resources.lib.data.shows.WINDOW')
    def test_adds_and_removes_combined(self, mock_window):
        """Should handle simultaneous adds and removes."""
        mock_window.getProperty.return_value = '[10, 20, 30]'
        storage = self._make_storage()
        storage.sync_tracked_shows.return_value = SyncResult(
            added={40}, removed={20}, revision=5
        )
        storage.get_ondeck_bulk.return_value = ({40: {}}, 5)
        logger = self._make_logger()

        sync_show_list_from_shared_db(storage, logger)

        call_args = mock_window.setProperty.call_args
        updated_ids = eval(call_args[0][1])
        assert set(updated_ids) == {10, 30, 40}

    @patch('resources.lib.data.shows.WINDOW')
    def test_sync_error_is_handled(self, mock_window):
        """Should log exception and return when sync_tracked_shows fails."""
        mock_window.getProperty.return_value = '[10, 20]'
        storage = self._make_storage()
        storage.sync_tracked_shows.side_effect = RuntimeError("DB error")
        logger = self._make_logger()

        sync_show_list_from_shared_db(storage, logger)

        logger.exception.assert_called_once()
        mock_window.setProperty.assert_not_called()

    @patch('resources.lib.data.shows.WINDOW')
    def test_add_fetch_failure_skips_add(self, mock_window):
        """Should not add shows if get_ondeck_bulk fails."""
        mock_window.getProperty.return_value = '[10, 20]'
        storage = self._make_storage()
        storage.sync_tracked_shows.return_value = SyncResult(
            added={30}, removed=set(), revision=5
        )
        storage.get_ondeck_bulk.side_effect = RuntimeError("Fetch error")
        logger = self._make_logger()

        sync_show_list_from_shared_db(storage, logger)

        # Property should still be updated (no adds, no removes = same set)
        # Actually, since added failed and removed is empty, property IS written
        # because sync_result.added was truthy
        call_args = mock_window.setProperty.call_args
        updated_ids = eval(call_args[0][1])
        assert set(updated_ids) == {10, 20}

    @patch('resources.lib.data.shows.WINDOW')
    def test_only_adds_successfully_fetched_shows(self, mock_window):
        """Should only add shows that get_ondeck_bulk returned data for."""
        mock_window.getProperty.return_value = '[10]'
        storage = self._make_storage()
        storage.sync_tracked_shows.return_value = SyncResult(
            added={20, 30}, removed=set(), revision=5
        )
        # Only show 20 was fetched successfully; 30 was missing
        storage.get_ondeck_bulk.return_value = ({20: {}}, 5)
        logger = self._make_logger()

        sync_show_list_from_shared_db(storage, logger)

        call_args = mock_window.setProperty.call_args
        updated_ids = eval(call_args[0][1])
        assert set(updated_ids) == {10, 20}

    @patch('resources.lib.data.shows.WINDOW')
    def test_invalid_property_value_returns_early(self, mock_window):
        """Should return early if property value is not valid Python."""
        mock_window.getProperty.return_value = 'not-a-list'
        storage = self._make_storage()

        sync_show_list_from_shared_db(storage)

        storage.sync_tracked_shows.assert_not_called()


# ── fetch_shows_with_watched_episodes ────────────────────────────────
class TestFetchShowsWithWatchedEpisodes:
    """A show is a Watched/Both candidate when it has >=1 WATCHED episode.

    Kodi's show-level ``playcount`` is a *fully-watched* flag (1 only when
    every episode is watched, computed as ``episode <= watchedepisodes`` -
    which is also 1 for a 0-episode show), NOT "has a watched episode". The
    real watched count is the ``watchedepisodes`` property. Selecting on
    ``playcount>0`` therefore drops partially-watched shows and pulls in
    empty shows. This test simulates Kodi faithfully so it fails against the
    playcount-based query and passes against a watchedepisodes-based one.
    """

    # (tvshowid, label, lastplayed, watchedepisodes, episode)
    LIBRARY = [
        (1, "Partial Show", "2026-01-01 10:00:00", 5, 15),   # partial -> include
        (2, "Done Show", "2026-01-02 10:00:00", 15, 15),     # fully watched -> include
        (3, "Fresh Show", "", 0, 10),                        # unwatched -> exclude
        # 0-episode show: watchedepisodes=0 but Kodi's playcount is 1 (0<=0),
        # so the old playcount-based query wrongly included it.
        (4, "Empty Show", "", 0, 0),                         # 0 episodes -> exclude
    ]

    def _fake_jsonrpc(self, request):
        import json
        params = json.loads(request).get("params", {})
        filt = params.get("filter") or {}
        rows = []
        for sid, label, lastplayed, watched, episode in self.LIBRARY:
            if filt.get("field") == "playcount":
                # Server-side playcount>0 = Kodi's fully-watched flag.
                if episode <= watched:
                    rows.append({"tvshowid": sid, "label": label,
                                 "lastplayed": lastplayed})
            else:
                rows.append({"tvshowid": sid, "label": label,
                             "lastplayed": lastplayed,
                             "watchedepisodes": watched, "episode": episode})
        return json.dumps({"result": {"tvshows": rows}})

    def test_includes_partially_watched_excludes_unwatched_and_empty(self):
        with patch("xbmc.executeJSONRPC", side_effect=self._fake_jsonrpc):
            result = fetch_shows_with_watched_episodes(
                sort_by=1, sort_reverse=False
            )
        ids = {row[1] for row in result}
        assert 1 in ids, (
            "partially-watched show dropped: selection uses show playcount "
            "(fully-watched flag) instead of watchedepisodes>0"
        )
        assert 2 in ids, "fully-watched show should be included"
        assert 3 not in ids, "unwatched show must not be a watched candidate"
        assert 4 not in ids, "empty (0-episode) show must not be included"
