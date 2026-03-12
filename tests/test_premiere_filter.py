"""Tests for 3-state premiere filtering logic in random_player.py."""
import pytest

from resources.lib.constants import PREMIERE_SKIP, PREMIERE_MIX_IN, PREMIERE_ONLY
from resources.lib.playback.random_player import (
    RandomPlaylistConfig,
    _check_premiere_exclusion,
    _remove_candidate,
)
from resources.lib.utils import get_logger


@pytest.fixture
def logger():
    return get_logger('test')


@pytest.fixture
def patch_window(mocker):
    """Patch WINDOW.getProperty to return controlled episode numbers."""
    mock_window = mocker.patch(
        'resources.lib.playback.random_player.WINDOW'
    )

    def setup(episode_map):
        """Set up episode_no values for show IDs.

        Args:
            episode_map: dict of show_id -> episode_no string (e.g. {1: 's01e01'})
        """
        def get_prop(key):
            for show_id, ep_no in episode_map.items():
                if key == f"EasyTV.{show_id}.EpisodeNo":
                    return ep_no
            return ''
        mock_window.getProperty.side_effect = get_prop

    return setup


class TestRemoveCandidate:
    def test_removes_existing_tag(self):
        candidates = ['t1', 't2', 't3']
        result = _remove_candidate(2, candidates)
        assert result is True
        assert candidates == ['t1', 't3']

    def test_missing_tag_returns_true(self):
        candidates = ['t1', 't3']
        result = _remove_candidate(2, candidates)
        assert result is True
        assert candidates == ['t1', 't3']


class TestCheckPremiereExclusionMixIn:
    """Both settings MIX_IN — nothing should be filtered."""

    def test_both_mixin_fast_path(self, patch_window, logger):
        patch_window({1: 's01e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False
        assert candidates == ['t1']

    def test_both_mixin_regular_episode(self, patch_window, logger):
        patch_window({1: 's02e05'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False


class TestCheckPremiereExclusionSkip:
    """SKIP mode — exclude that premiere type, keep others."""

    def test_skip_series_excludes_s01e01(self, patch_window, logger):
        patch_window({1: 's01e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_SKIP, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True
        assert candidates == []

    def test_skip_series_keeps_season_premiere(self, patch_window, logger):
        patch_window({1: 's02e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_SKIP, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False
        assert candidates == ['t1']

    def test_skip_series_keeps_regular(self, patch_window, logger):
        patch_window({1: 's02e05'})
        config = RandomPlaylistConfig(premieres=PREMIERE_SKIP, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False

    def test_skip_season_excludes_s02e01(self, patch_window, logger):
        patch_window({1: 's02e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_SKIP)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True
        assert candidates == []

    def test_skip_season_keeps_series_premiere(self, patch_window, logger):
        patch_window({1: 's01e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_SKIP)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False
        assert candidates == ['t1']

    def test_skip_season_keeps_regular(self, patch_window, logger):
        patch_window({1: 's03e05'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_SKIP)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False


class TestCheckPremiereExclusionOnly:
    """ONLY mode — non-premieres excluded, SKIP type also excluded."""

    def test_series_only_keeps_s01e01(self, patch_window, logger):
        patch_window({1: 's01e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False
        assert candidates == ['t1']

    def test_series_only_keeps_season_premiere(self, patch_window, logger):
        """Season=MIX_IN with series=ONLY → all premieres included."""
        patch_window({1: 's02e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False

    def test_series_only_excludes_regular(self, patch_window, logger):
        patch_window({1: 's02e05'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True
        assert candidates == []

    def test_series_only_season_skip_excludes_season_premiere(self, patch_window, logger):
        patch_window({1: 's02e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_SKIP)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True

    def test_series_only_season_skip_keeps_series_premiere(self, patch_window, logger):
        patch_window({1: 's01e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_SKIP)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False

    def test_season_only_keeps_season_premiere(self, patch_window, logger):
        patch_window({1: 's03e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_ONLY)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False

    def test_season_only_keeps_series_premiere(self, patch_window, logger):
        """Series=MIX_IN with season=ONLY → all premieres included."""
        patch_window({1: 's01e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_ONLY)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False

    def test_season_only_excludes_regular(self, patch_window, logger):
        patch_window({1: 's03e05'})
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_ONLY)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True

    def test_season_only_series_skip_excludes_series_premiere(self, patch_window, logger):
        patch_window({1: 's01e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_SKIP, season_premieres=PREMIERE_ONLY)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True

    def test_both_only_keeps_all_premieres(self, patch_window, logger):
        patch_window({1: 's01e01', 2: 's03e01'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_ONLY)
        candidates = ['t1', 't2']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False
        assert _check_premiere_exclusion(2, candidates, config, logger) is False
        assert candidates == ['t1', 't2']

    def test_both_only_excludes_regular(self, patch_window, logger):
        patch_window({1: 's02e05'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_ONLY)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True
        assert candidates == []


class TestCheckPremiereExclusionEdgeCases:
    """Edge cases: missing/unparseable episode data."""

    def test_no_episode_data_mixin(self, patch_window, logger):
        patch_window({})  # No data for show 1
        config = RandomPlaylistConfig(premieres=PREMIERE_MIX_IN, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False

    def test_no_episode_data_only_mode(self, patch_window, logger):
        patch_window({})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True
        assert candidates == []

    def test_unparseable_episode_mixin(self, patch_window, logger):
        patch_window({1: 'invalid'})
        config = RandomPlaylistConfig(premieres=PREMIERE_SKIP, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is False

    def test_unparseable_episode_only_mode(self, patch_window, logger):
        patch_window({1: 'invalid'})
        config = RandomPlaylistConfig(premieres=PREMIERE_ONLY, season_premieres=PREMIERE_MIX_IN)
        candidates = ['t1']
        assert _check_premiere_exclusion(1, candidates, config, logger) is True
