"""Tests for the guided-flow show filter engine."""
from resources.lib.constants import (
    EPISODE_SELECTION_BOTH,
    EPISODE_SELECTION_UNWATCHED,
    EPISODE_SELECTION_WATCHED,
)
from resources.lib.data.show_filters import (
    ShowFilterConfig,
    apply_show_filters,
    eligible_episode_count,
    extract_decade_buckets,
    extract_unique_genres,
)


def _show(showid, genre=None, year=2020, rating=7.5, episode=10, watched=4):
    return {"tvshowid": showid, "genre": genre or [], "year": year,
            "rating": rating, "episode": episode, "watchedepisodes": watched}


SHOWS = [
    _show(1, ["Comedy"], year=2023, rating=8.2, episode=20, watched=0),
    _show(2, ["Drama", "Crime"], year=1999, rating=9.1, episode=60, watched=60),
    _show(3, ["Comedy", "Animation"], year=2012, rating=6.5, episode=8, watched=6),
    _show(4, ["Horror"], year=2021, rating=7.0, episode=3, watched=1),
]


class TestEligibleEpisodeCount:
    def test_unwatched(self):
        assert eligible_episode_count(SHOWS[1], EPISODE_SELECTION_UNWATCHED) == 0
        assert eligible_episode_count(SHOWS[0], EPISODE_SELECTION_UNWATCHED) == 20

    def test_watched(self):
        assert eligible_episode_count(SHOWS[1], EPISODE_SELECTION_WATCHED) == 60
        assert eligible_episode_count(SHOWS[0], EPISODE_SELECTION_WATCHED) == 0

    def test_both(self):
        assert eligible_episode_count(SHOWS[2], EPISODE_SELECTION_BOTH) == 8

    def test_missing_fields_are_zero(self):
        assert eligible_episode_count({}, EPISODE_SELECTION_UNWATCHED) == 0


class TestApplyShowFilters:
    def _ids(self, result):
        return sorted(s["tvshowid"] for s in result)

    def test_no_filters_returns_all(self):
        out = apply_show_filters(SHOWS, ShowFilterConfig(), EPISODE_SELECTION_BOTH)
        assert self._ids(out) == [1, 2, 3, 4]

    def test_ignore_genres_excludes_any_match(self):
        cfg = ShowFilterConfig(ignore_genres=["Comedy"])
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert self._ids(out) == [2, 4]

    def test_genres_keeps_any_match(self):
        cfg = ShowFilterConfig(genres=["Comedy", "Horror"])
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert self._ids(out) == [1, 3, 4]

    def test_duration_bounds_in_minutes(self):
        durations = {1: 22 * 60, 2: 45 * 60, 3: 0, 4: 60 * 60}
        cfg = ShowFilterConfig(duration_min=0, duration_max=30)
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH,
                                 durations=durations)
        # show 3 has no cached duration and must be kept, not excluded
        assert self._ids(out) == [1, 3]

    def test_duration_min_bound(self):
        durations = {1: 22 * 60, 2: 45 * 60, 3: 50 * 60, 4: 60 * 60}
        cfg = ShowFilterConfig(duration_min=45)
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH,
                                 durations=durations)
        assert self._ids(out) == [2, 3, 4]

    def test_duration_filter_without_lookup_keeps_all(self):
        cfg = ShowFilterConfig(duration_max=30)
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert self._ids(out) == [1, 2, 3, 4]

    def test_year_range(self):
        cfg = ShowFilterConfig(year_from=2010, year_to=2019)
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert self._ids(out) == [3]

    def test_year_from_only(self):
        cfg = ShowFilterConfig(year_from=2021)
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert self._ids(out) == [1, 4]

    def test_min_rating(self):
        cfg = ShowFilterConfig(min_rating=8.0)
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert self._ids(out) == [1, 2]

    def test_depth_respects_episode_selection(self):
        cfg = ShowFilterConfig(min_eligible_episodes=10)
        unwatched = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_UNWATCHED)
        assert self._ids(unwatched) == [1]
        watched = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_WATCHED)
        assert self._ids(watched) == [2]
        both = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert self._ids(both) == [1, 2]

    def test_combined_filters(self):
        cfg = ShowFilterConfig(genres=["Comedy"], min_rating=7.0,
                               min_eligible_episodes=10)
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_UNWATCHED)
        assert self._ids(out) == [1]

    def test_zero_result(self):
        cfg = ShowFilterConfig(genres=["Western"])
        out = apply_show_filters(SHOWS, cfg, EPISODE_SELECTION_BOTH)
        assert out == []


class TestExtractors:
    def test_unique_genres_sorted(self):
        assert extract_unique_genres(SHOWS) == [
            "Animation", "Comedy", "Crime", "Drama", "Horror"]

    def test_decade_buckets_descending_with_counts(self):
        buckets = extract_decade_buckets(SHOWS)
        assert buckets == [(2020, 2, "2020s"), (2010, 1, "2010s"),
                           (1990, 1, "1990s")]

    def test_decade_buckets_skip_year_zero(self):
        shows = SHOWS + [_show(9, year=0)]
        assert extract_decade_buckets(shows) == extract_decade_buckets(SHOWS)


class TestResolveCandidateShowIds:
    def test_population_only(self, mocker):
        mocker.patch(
            "resources.lib.data.show_filters.filter_shows_by_population",
            return_value=[["k", 1, 11], ["k", 2, 22]])
        from resources.lib.constants import PREMIERE_MIX_IN
        from resources.lib.data.show_filters import resolve_candidate_show_ids
        ids = resolve_candidate_show_ids(
            {"none": ""}, 0, PREMIERE_MIX_IN, PREMIERE_MIX_IN)
        assert ids == {1, 2}

    def test_premiere_gate_applied_when_filtering_mode(self, mocker):
        mocker.patch(
            "resources.lib.data.show_filters.filter_shows_by_population",
            return_value=[["k", 1, 11], ["k", 2, 22]])
        mocker.patch(
            "resources.lib.data.show_filters.fetch_inprogress_episode_ids",
            return_value=set())
        gate = mocker.patch(
            "resources.lib.data.show_filters.should_include_show",
            side_effect=lambda sid, *a, **kw: sid == 2)
        from resources.lib.constants import PREMIERE_MIX_IN, PREMIERE_SKIP
        from resources.lib.data.show_filters import resolve_candidate_show_ids
        ids = resolve_candidate_show_ids(
            {"none": ""}, 0, PREMIERE_SKIP, PREMIERE_MIX_IN)
        assert ids == {2}
        assert gate.called

    def test_premiere_gate_bypassed_in_mix_in(self, mocker):
        mocker.patch(
            "resources.lib.data.show_filters.filter_shows_by_population",
            return_value=[["k", 3, 33]])
        gate = mocker.patch(
            "resources.lib.data.show_filters.should_include_show")
        from resources.lib.constants import PREMIERE_MIX_IN
        from resources.lib.data.show_filters import resolve_candidate_show_ids
        ids = resolve_candidate_show_ids(
            {"none": ""}, 0, PREMIERE_MIX_IN, PREMIERE_MIX_IN)
        assert ids == {3}
        assert not gate.called


class TestRestrictToAllowed:
    def test_none_means_no_restriction(self):
        from resources.lib.data.show_filters import restrict_to_allowed
        data = [["k", 1, 11], ["k", 2, 22]]
        assert restrict_to_allowed(data, None) == data

    def test_intersection(self):
        from resources.lib.data.show_filters import restrict_to_allowed
        data = [["k", 1, 11], ["k", 2, 22], ["k", 3, 33]]
        assert restrict_to_allowed(data, {2, 3}) == [["k", 2, 22], ["k", 3, 33]]

    def test_empty_allowed_set_removes_all(self):
        from resources.lib.data.show_filters import restrict_to_allowed
        assert restrict_to_allowed([["k", 1, 11]], set()) == []
