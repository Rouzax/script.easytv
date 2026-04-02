"""Tests for browse mode premiere filter with resume state awareness."""
import pytest


@pytest.fixture
def patch_window(mocker):
    """Patch WINDOW.getProperty to return controlled values."""
    mock_window = mocker.patch(
        'resources.lib.playback.browse_mode.WINDOW'
    )

    def setup(prop_map):
        """Set up window property values.

        Args:
            prop_map: dict of property_key -> value string
        """
        def get_prop(key):
            return prop_map.get(key, '')
        mock_window.getProperty.side_effect = get_prop

    return setup


def _make_should_include(series_premieres, season_premieres):
    """Create should_include function with given premiere settings.

    Mirrors the closure from browse_mode.build_episode_list() so we
    can test the filtering logic in isolation.
    """
    from resources.lib.constants import PREMIERE_ONLY, PREMIERE_SKIP
    from resources.lib.playback.browse_mode import WINDOW

    only_mode = (series_premieres == PREMIERE_ONLY
                 or season_premieres == PREMIERE_ONLY)

    class _Cfg:
        pass
    config = _Cfg()
    config.series_premieres = series_premieres
    config.season_premieres = season_premieres

    def should_include(show_entry):
        episode_no = WINDOW.getProperty(f"EasyTV.{show_entry[1]}.EpisodeNo")
        if not episode_no or len(episode_no) < 6:
            return not only_mode
        try:
            season_num = int(episode_no[1:3])
            episode_num = int(episode_no[4:6])
        except (ValueError, IndexError):
            return not only_mode

        is_premiere = (episode_num == 1)

        # In-progress premieres are always included (user is actively watching)
        if is_premiere:
            resume = WINDOW.getProperty(f"EasyTV.{show_entry[1]}.Resume")
            if resume == "true":
                return True

        if only_mode:
            if not is_premiere:
                return False
            if season_num == 1 and config.series_premieres == PREMIERE_SKIP:
                return False
            if season_num > 1 and config.season_premieres == PREMIERE_SKIP:
                return False
            return True
        else:
            if not is_premiere:
                return True
            if season_num == 1:
                return config.series_premieres != PREMIERE_SKIP
            return config.season_premieres != PREMIERE_SKIP

    return should_include


class TestShouldIncludeResumeState:
    """Premiere filter should include in-progress premieres."""

    def test_season_premiere_with_resume_included(self, patch_window):
        """S02E01 with resume=true should be included even with SKIP."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 318, '5996']) is True

    def test_season_premiere_without_resume_excluded(self, patch_window):
        """S02E01 with resume=false should be excluded with SKIP."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'false',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 318, '5996']) is False

    def test_series_premiere_with_resume_included(self, patch_window):
        """S01E01 with resume=true should be included even with SKIP."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.100.EpisodeNo': 'S01E01',
            'EasyTV.100.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 100, '1234']) is True

    def test_non_premiere_unaffected(self, patch_window):
        """S02E17 should be included regardless of resume state."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.135.EpisodeNo': 'S02E17',
            'EasyTV.135.Resume': 'false',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 135, '6840']) is True

    def test_premiere_with_mix_in_unaffected(self, patch_window):
        """With MIX_IN, premieres are always included (resume irrelevant)."""
        from resources.lib.constants import PREMIERE_MIX_IN
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'false',
        })
        should_include = _make_should_include(PREMIERE_MIX_IN, PREMIERE_MIX_IN)
        assert should_include([0, 318, '5996']) is True

    def test_premiere_no_resume_property_excluded(self, patch_window):
        """S02E01 with no Resume property should be excluded with SKIP."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 318, '5996']) is False
