"""Tests using frozen snapshots from the Kodi test instance (vm2.home.lan).

All data was fetched once and embedded as constants. Tests run offline —
no Kodi instance needed at test time.

Data source: vm2.home.lan:8080 (MariaDB backend, 286 shows, 4452 episodes)
Snapshot date: 2026-03-12
"""
from resources.lib.data.duration_cache import calculate_median_duration
from resources.lib.data.shows import (
    generate_sort_key,
    get_episode_sort_key,
    _get_playlist_filename,
    parse_season_episode_string,
)


# =============================================================================
# Frozen data from Kodi instance
# =============================================================================

# "1923" (tvshowid=2) — all 15 episodes, durations in seconds
# S01E01-E08 + S02E01-E07. S02E07 is a double-length finale (6701s).
SHOW_1923_DURATIONS = [
    3633, 2866, 3454, 3321, 4202, 3278, 3123, 4060,  # S01
    3490, 3224, 3520, 3501, 3165, 3022, 6701,         # S02
]

# Full streamdetails dicts exactly as returned by Kodi JSON-RPC.
# Includes audio, subtitle, and video sub-dicts present in production data.
REAL_STREAMDETAILS_EPISODES = [
    {
        'streamdetails': {
            'audio': [{'channels': 6, 'codec': 'eac3', 'language': 'eng'}],
            'subtitle': [
                {'language': 'eng'}, {'language': 'eng'}, {'language': 'dut'}
            ],
            'video': [{
                'aspect': 1.7777800559997559, 'codec': 'hevc',
                'duration': 3633, 'hdrtype': '', 'height': 2160,
                'language': '', 'stereomode': '', 'width': 3840,
            }],
        }
    },
    {
        'streamdetails': {
            'audio': [{'channels': 6, 'codec': 'eac3', 'language': 'eng'}],
            'subtitle': [
                {'language': 'eng'}, {'language': 'eng'}, {'language': 'dut'}
            ],
            'video': [{
                'aspect': 1.7777800559997559, 'codec': 'hevc',
                'duration': 2866, 'hdrtype': '', 'height': 2160,
                'language': 'eng', 'stereomode': '', 'width': 3840,
            }],
        }
    },
]

# SMB file paths from "1923" episodes
REAL_SMB_PATHS = [
    "smb://HYPERV/Data/TVSeries/EN/1923 (2022)/Season 01/1923 - S01E01 - [2160p.WEB.h265]-[glhf].mkv",
    "smb://HYPERV/Data/TVSeries/EN/1923 (2022)/Season 01/1923 - S01E02 - [2160p.WEB.h265]-[TRUFFLE].mkv",
    "smb://HYPERV/Data/TVSeries/EN/1923 (2022)/Season 02/1923 - S02E07 - [2160p.WEB-DL.h265]-[FLUX].mkv",
]

# Euphoria specials — both non-positioned (specialsortseason=-1)
EUPHORIA_SPECIALS = [
    {'season': 0, 'episode': 1, 'specialsortseason': -1, 'specialsortepisode': -1,
     'title': "Trouble Don't Last Always"},
    {'season': 0, 'episode': 2, 'specialsortseason': -1, 'specialsortepisode': -1,
     'title': "F**k Anyone Who's Not A Sea Blob"},
]


# =============================================================================
# Tests
# =============================================================================

class TestMedianDurationRealData:
    """Median calculation against real "1923" episode durations."""

    def _episodes_from_durations(self, durations):
        return [{'streamdetails': {'video': [{'duration': d}]}} for d in durations]

    def test_1923_all_15_episodes(self):
        """Median of all 15 episodes including double-length finale."""
        eps = self._episodes_from_durations(SHOW_1923_DURATIONS)
        # Sorted: [2866,3022,3123,3165,3224,3278,3321,3454,3490,3501,3520,3633,4060,4202,6701]
        # Middle (index 7) = 3454
        assert calculate_median_duration(eps) == 3454

    def test_1923_season_1_only(self):
        """Median of 8 S01 episodes (even count)."""
        eps = self._episodes_from_durations(SHOW_1923_DURATIONS[:8])
        # Sorted: [2866,3123,3278,3321,3454,3633,4060,4202]
        # Average of indices 3,4 = (3321+3454)//2 = 3387
        assert calculate_median_duration(eps) == 3387

    def test_double_length_finale_doesnt_skew_median(self):
        """S02E07 is 6701s (~112min) vs typical ~55min. Median is robust."""
        eps = self._episodes_from_durations(SHOW_1923_DURATIONS)
        median = calculate_median_duration(eps)
        # Median should be around 3454s (~57min), not pulled toward 6701s
        assert 3000 <= median <= 4000


class TestStreamdetailsShape:
    """Verify calculate_median_duration handles real Kodi streamdetails shape.

    Production streamdetails include audio, subtitle, and video sub-dicts
    with many fields beyond just duration. This ensures we correctly
    navigate the nested structure.
    """

    def test_real_streamdetails_extracts_duration(self):
        median = calculate_median_duration(REAL_STREAMDETAILS_EPISODES)
        # (3633 + 2866) // 2 = 3249
        assert median == 3249

    def test_mixed_real_and_empty_streamdetails(self):
        """Real episode + episode with empty video list."""
        eps = REAL_STREAMDETAILS_EPISODES + [
            {'streamdetails': {'audio': [], 'subtitle': [], 'video': []}}
        ]
        # Empty video excluded, still (3633 + 2866) // 2 = 3249
        assert calculate_median_duration(eps) == 3249


class TestSortKeyRealTitles:
    """Article stripping with actual show titles from the library."""

    def test_dutch_de_snorkels(self):
        assert generate_sort_key("De Snorkels", "Dutch") == "snorkels"

    def test_english_the_alienist(self):
        assert generate_sort_key("The Alienist", "English") == "alienist"

    def test_english_a_man_in_full(self):
        assert generate_sort_key("A Man in Full", "English") == "man in full"

    def test_numeric_title_no_article(self):
        """Numeric titles like '1923' have no article to strip."""
        assert generate_sort_key("1923", "English") == "1923"

    def test_no_article_euphoria(self):
        assert generate_sort_key("Euphoria", "English") == "euphoria"

    def test_dutch_title_with_english_language(self):
        """Dutch article 'De' is NOT stripped when language is English."""
        assert generate_sort_key("De Snorkels", "English") == "de snorkels"


class TestEpisodeSortKeyRealSpecials:
    """Sort key behavior with Euphoria's actual specials."""

    def test_euphoria_special_non_positioned(self):
        """S00E01 with specialsortseason=-1 sorts as regular S00E01."""
        key = get_episode_sort_key(EUPHORIA_SPECIALS[0], include_positioned_specials=True)
        assert key == (0, 1, 0, 1)

    def test_euphoria_specials_sort_before_s01(self):
        """Non-positioned specials (season 0) sort before season 1."""
        special_key = get_episode_sort_key(
            EUPHORIA_SPECIALS[0], include_positioned_specials=True
        )
        regular_key = get_episode_sort_key(
            {'season': 1, 'episode': 1}, include_positioned_specials=True
        )
        assert special_key < regular_key

    def test_euphoria_specials_order(self):
        """S00E01 sorts before S00E02."""
        k1 = get_episode_sort_key(EUPHORIA_SPECIALS[0], include_positioned_specials=True)
        k2 = get_episode_sort_key(EUPHORIA_SPECIALS[1], include_positioned_specials=True)
        assert k1 < k2


class TestPlaylistFilenameRealPaths:
    """Basename extraction from actual SMB file paths."""

    def test_smb_path_s01e01(self):
        result = _get_playlist_filename(REAL_SMB_PATHS[0])
        assert result == "1923 - S01E01 - [2160p.WEB.h265]-[glhf].mkv"

    def test_smb_path_s01e02(self):
        result = _get_playlist_filename(REAL_SMB_PATHS[1])
        assert result == "1923 - S01E02 - [2160p.WEB.h265]-[TRUFFLE].mkv"

    def test_smb_path_s02e07(self):
        result = _get_playlist_filename(REAL_SMB_PATHS[2])
        assert result == "1923 - S02E07 - [2160p.WEB-DL.h265]-[FLUX].mkv"

    def test_smb_paths_are_not_plugin_urls(self):
        """SMB paths should extract basename, not return full path."""
        for path in REAL_SMB_PATHS:
            result = _get_playlist_filename(path)
            assert not result.startswith("smb://")


class TestParseSeasonEpisodeRealData:
    """Two-digit padding with real season/episode numbers from library."""

    def test_single_digit_episodes(self):
        """1923 S01E01-E08 and S02E01-E07 all have single-digit episodes."""
        for ep_num in range(1, 9):
            assert parse_season_episode_string(ep_num) == f"{ep_num:02d}"

    def test_seasons(self):
        assert parse_season_episode_string(1) == "01"
        assert parse_season_episode_string(2) == "02"

    def test_euphoria_special_season_zero(self):
        assert parse_season_episode_string(0) == "00"
