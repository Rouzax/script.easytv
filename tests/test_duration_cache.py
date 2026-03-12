"""Tests for resources/lib/data/duration_cache.py — duration calculations."""
from resources.lib.data.duration_cache import (
    calculate_median_duration,
    get_shows_needing_calculation,
    build_updated_cache,
)
from resources.lib.constants import DURATION_CACHE_VERSION


def _make_episode(duration):
    """Helper to create an episode dict with streamdetails."""
    return {'streamdetails': {'video': [{'duration': duration}]}}


# ── calculate_median_duration ────────────────────────────────────────

class TestCalculateMedianDuration:
    def test_odd_count(self):
        eps = [_make_episode(100), _make_episode(200), _make_episode(300)]
        assert calculate_median_duration(eps) == 200

    def test_even_count(self):
        eps = [_make_episode(100), _make_episode(200), _make_episode(300), _make_episode(400)]
        assert calculate_median_duration(eps) == 250

    def test_empty_list(self):
        assert calculate_median_duration([]) == 0

    def test_single_episode(self):
        assert calculate_median_duration([_make_episode(500)]) == 500

    def test_zero_duration_excluded(self):
        eps = [_make_episode(0), _make_episode(200), _make_episode(300)]
        assert calculate_median_duration(eps) == 250

    def test_missing_streamdetails_excluded(self):
        eps = [
            {'streamdetails': {'video': []}},
            _make_episode(200),
            _make_episode(300),
        ]
        assert calculate_median_duration(eps) == 250

    def test_all_zero_returns_zero(self):
        eps = [_make_episode(0), _make_episode(0)]
        assert calculate_median_duration(eps) == 0


# ── get_shows_needing_calculation ────────────────────────────────────

class TestGetShowsNeedingCalculation:
    def _cache(self, shows_dict):
        return {'version': DURATION_CACHE_VERSION, 'shows': shows_dict}

    def test_new_show_included(self):
        cache = self._cache({})
        result = get_shows_needing_calculation(cache, {100: 10})
        assert 100 in result

    def test_unchanged_show_excluded(self):
        cache = self._cache({'100': {'median_seconds': 2000, 'episode_count': 10}})
        result = get_shows_needing_calculation(cache, {100: 10})
        assert 100 not in result

    def test_count_changed_included(self):
        cache = self._cache({'100': {'median_seconds': 2000, 'episode_count': 10}})
        result = get_shows_needing_calculation(cache, {100: 15})
        assert 100 in result

    def test_cached_zero_median_retried(self):
        cache = self._cache({'100': {'median_seconds': 0, 'episode_count': 10}})
        result = get_shows_needing_calculation(cache, {100: 10})
        assert 100 in result

    def test_pruned_show_not_in_result(self):
        cache = self._cache({'999': {'median_seconds': 1000, 'episode_count': 5}})
        result = get_shows_needing_calculation(cache, {100: 10})
        assert 999 not in result


# ── build_updated_cache ──────────────────────────────────────────────

class TestBuildUpdatedCache:
    def _cache(self, shows_dict):
        return {'version': DURATION_CACHE_VERSION, 'shows': shows_dict}

    def test_preserves_unchanged(self):
        old = self._cache({'100': {'median_seconds': 2000, 'episode_count': 10, 'title': 'A'}})
        result = build_updated_cache(old, {100: 10}, {}, {100: 'A'})
        assert '100' in result['shows']
        assert result['shows']['100']['median_seconds'] == 2000

    def test_adds_new_duration(self):
        old = self._cache({})
        result = build_updated_cache(old, {200: 10}, {200: 1800}, {200: 'Show B'})
        assert '200' in result['shows']
        assert result['shows']['200']['median_seconds'] == 1800

    def test_prunes_missing_show(self):
        old = self._cache({'999': {'median_seconds': 1000, 'episode_count': 5, 'title': 'Gone'}})
        result = build_updated_cache(old, {100: 10}, {100: 2000}, {100: 'New'})
        assert '999' not in result['shows']

    def test_zero_median_excluded(self):
        old = self._cache({})
        result = build_updated_cache(old, {100: 10}, {100: 0}, {100: 'Show'})
        assert '100' not in result['shows']

    def test_version_set(self):
        result = build_updated_cache(self._cache({}), {}, {}, {})
        assert result['version'] == DURATION_CACHE_VERSION

    def test_title_updated_for_preserved(self):
        old = self._cache({'100': {'median_seconds': 2000, 'episode_count': 10, 'title': 'Old Name'}})
        result = build_updated_cache(old, {100: 10}, {}, {100: 'New Name'})
        assert result['shows']['100']['title'] == 'New Name'
