"""Tests for resources/lib/data/shows.py — show data logic."""
from resources.lib.data.shows import (
    generate_sort_key,
    parse_season_episode_string,
    get_episode_sort_key,
    get_show_category,
    get_premiere_category,
    _get_playlist_filename,
)
from resources.lib.constants import (
    CATEGORY_START_FRESH,
    CATEGORY_CONTINUE_WATCHING,
    CATEGORY_SHOW_PREMIERE,
    CATEGORY_SEASON_PREMIERE,
)


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
