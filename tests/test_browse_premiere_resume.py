"""Tests for browse mode premiere filter with resume state awareness."""
import pytest


@pytest.fixture
def patch_window(mocker):
    """Patch WINDOW.getProperty to return controlled values."""
    mock_window = mocker.patch(
        'resources.lib.data.show_filters.WINDOW'
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
    """Bind the production premiere filter to the given settings.

    Calls the real should_include_show so these tests cannot pass against a
    mirrored copy of the logic while production behaves differently.
    """
    from resources.lib.data.show_filters import should_include_show

    def should_include(show_entry):
        return should_include_show(
            show_entry[1], series_premieres, season_premieres
        )

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


class TestOnlyModeRespectsPremiereType:
    """In "premieres only" mode the type IS the list.

    The in-progress override must not smuggle in a premiere of the type the
    user excluded: a part-watched S01E01 showing up in a season-premiere-only
    list, or a part-watched S02E01 in a series-premiere-only list.
    """

    def test_season_only_excludes_in_progress_series_premiere(self, patch_window):
        from resources.lib.constants import PREMIERE_ONLY, PREMIERE_SKIP
        patch_window({
            'EasyTV.347.EpisodeNo': 'S01E01',
            'EasyTV.347.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_ONLY)
        assert should_include([0, 347, '5157']) is False

    def test_series_only_excludes_in_progress_season_premiere(self, patch_window):
        from resources.lib.constants import PREMIERE_ONLY, PREMIERE_SKIP
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_ONLY, PREMIERE_SKIP)
        assert should_include([0, 318, '5996']) is False

    def test_season_only_keeps_in_progress_season_premiere(self, patch_window):
        """The allowed type is still kept, resume or not."""
        from resources.lib.constants import PREMIERE_ONLY, PREMIERE_SKIP
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_ONLY)
        assert should_include([0, 318, '5996']) is True

    def test_series_only_keeps_in_progress_series_premiere(self, patch_window):
        from resources.lib.constants import PREMIERE_ONLY, PREMIERE_SKIP
        patch_window({
            'EasyTV.347.EpisodeNo': 'S01E01',
            'EasyTV.347.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_ONLY, PREMIERE_SKIP)
        assert should_include([0, 347, '5157']) is True

    def test_only_mode_still_excludes_non_premieres(self, patch_window):
        from resources.lib.constants import PREMIERE_ONLY, PREMIERE_SKIP
        patch_window({
            'EasyTV.135.EpisodeNo': 'S02E17',
            'EasyTV.135.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_ONLY)
        assert should_include([0, 135, '6840']) is False

    def test_skip_mode_override_is_unchanged(self, patch_window):
        """The in-progress clone (SKIP/SKIP) must keep its override."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.347.EpisodeNo': 'S01E01',
            'EasyTV.347.Resume': 'true',
        })
        should_include = _make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 347, '5157']) is True


class TestInProgressSetDrivesTheOverride:
    """The in-progress override reads Kodi's live in-progress set, not the
    per-show Resume property.

    The property is a cache of Kodi's resume state, and a peer's partial watch
    changes that state without moving the on-deck episode, so this box could
    hold Resume="false" indefinitely. Consulting Kodi directly removes the
    staleness entirely, and one filtered query answers it for the whole library
    (~114ms) versus ~86ms per show asked individually.
    """

    def test_premiere_kept_when_ondeck_episode_is_in_progress(self, patch_window):
        from resources.lib.constants import PREMIERE_SKIP
        from resources.lib.data.show_filters import should_include_show
        patch_window({
            "EasyTV.7.EpisodeNo": "S01E01",
            "EasyTV.7.EpisodeID": "1234",
            "EasyTV.7.Resume": "false",   # stale cache says not in progress
        })
        assert should_include_show(
            7, PREMIERE_SKIP, PREMIERE_SKIP, inprogress_ids={1234}
        ) is True

    def test_premiere_dropped_when_ondeck_episode_not_in_progress(self, patch_window):
        from resources.lib.constants import PREMIERE_SKIP
        from resources.lib.data.show_filters import should_include_show
        patch_window({
            "EasyTV.7.EpisodeNo": "S01E01",
            "EasyTV.7.EpisodeID": "1234",
            "EasyTV.7.Resume": "true",    # stale cache says in progress
        })
        assert should_include_show(
            7, PREMIERE_SKIP, PREMIERE_SKIP, inprogress_ids=set()
        ) is False

    def test_falls_back_to_property_when_no_set_supplied(self, patch_window):
        """Callers that do not pass a set keep the previous behaviour."""
        from resources.lib.constants import PREMIERE_SKIP
        from resources.lib.data.show_filters import should_include_show
        patch_window({
            "EasyTV.7.EpisodeNo": "S01E01",
            "EasyTV.7.Resume": "true",
        })
        assert should_include_show(7, PREMIERE_SKIP, PREMIERE_SKIP) is True

    def test_unparseable_episode_id_is_not_in_progress(self, patch_window):
        from resources.lib.constants import PREMIERE_SKIP
        from resources.lib.data.show_filters import should_include_show
        patch_window({
            "EasyTV.7.EpisodeNo": "S01E01",
            "EasyTV.7.EpisodeID": "",
        })
        assert should_include_show(
            7, PREMIERE_SKIP, PREMIERE_SKIP, inprogress_ids={1234}
        ) is False
