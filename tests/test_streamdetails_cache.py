"""Tests for resources/lib/data/streamdetails_cache.py — per-episode stream info cache."""
from resources.lib.constants import STREAMDETAILS_CACHE_VERSION
from resources.lib.data.streamdetails_cache import (
    build_updated_streamdetails_cache,
    extract_episode_streamdetails,
    format_resolution,
    get_episode_duration,
    get_shows_needing_streamdetails,
)


def _make_episode(episode_id, duration=2580, height=1080, video_codec="h264",
                  hdr="", audio_codec="aac", channels=2, subtitles=None):
    """Helper to create an episode dict with full streamdetails."""
    subs = subtitles or []
    return {
        'episodeid': episode_id,
        'streamdetails': {
            'video': [{
                'duration': duration,
                'height': height,
                'codec': video_codec,
                'hdrtype': hdr,
            }],
            'audio': [{
                'codec': audio_codec,
                'channels': channels,
                'language': 'eng',
            }],
            'subtitle': [{'language': lang} for lang in subs],
        }
    }


# ── extract_episode_streamdetails ───────────────────────────────────

class TestExtractEpisodeStreamdetails:
    def test_standard_episode(self):
        eps = [_make_episode(100, duration=3633, height=2160,
                             video_codec="hevc", hdr="dolbyvision",
                             audio_codec="eac3", channels=6,
                             subtitles=["eng", "dut"])]
        result = extract_episode_streamdetails(eps)
        assert 100 in result
        assert result[100] == {
            'duration': 3633,
            'resolution': '2160p',
            'video_codec': 'hevc',
            'hdr': 'dolbyvision',
            'audio_codec': 'eac3',
            'channels': 6,
            'subtitles': ['eng', 'dut'],
        }

    def test_missing_streamdetails_key(self):
        eps = [{'episodeid': 100}]
        result = extract_episode_streamdetails(eps)
        assert 100 not in result

    def test_empty_video_array(self):
        eps = [{'episodeid': 100, 'streamdetails': {'video': [], 'audio': [], 'subtitle': []}}]
        result = extract_episode_streamdetails(eps)
        assert 100 not in result

    def test_empty_audio_array(self):
        eps = [{'episodeid': 100, 'streamdetails': {
            'video': [{'duration': 2580, 'height': 1080, 'codec': 'h264', 'hdrtype': ''}],
            'audio': [],
            'subtitle': [],
        }}]
        result = extract_episode_streamdetails(eps)
        assert result[100]['audio_codec'] == ''
        assert result[100]['channels'] == 0

    def test_empty_subtitle_array(self):
        eps = [_make_episode(100, subtitles=[])]
        result = extract_episode_streamdetails(eps)
        assert result[100]['subtitles'] == []

    def test_zero_duration_still_stored(self):
        eps = [_make_episode(100, duration=0)]
        result = extract_episode_streamdetails(eps)
        assert 100 in result
        assert result[100]['duration'] == 0

    def test_missing_episodeid(self):
        eps = [{'streamdetails': {'video': [{'duration': 100, 'height': 720,
                                             'codec': 'h264', 'hdrtype': ''}],
                                  'audio': [], 'subtitle': []}}]
        result = extract_episode_streamdetails(eps)
        assert len(result) == 0

    def test_multiple_episodes(self):
        eps = [_make_episode(1, duration=100), _make_episode(2, duration=200)]
        result = extract_episode_streamdetails(eps)
        assert len(result) == 2
        assert result[1]['duration'] == 100
        assert result[2]['duration'] == 200

    def test_duplicate_subtitle_languages(self):
        eps = [_make_episode(100, subtitles=["eng", "eng", "dut", "eng"])]
        result = extract_episode_streamdetails(eps)
        subs = result[100]['subtitles']
        assert subs == ['eng', 'dut']

    def test_empty_episode_list(self):
        result = extract_episode_streamdetails([])
        assert result == {}


# ── format_resolution ───────────────────────────────────────────────

class TestFormatResolution:
    def test_4k(self):
        assert format_resolution(2160) == '2160p'

    def test_above_4k(self):
        assert format_resolution(4320) == '2160p'

    def test_1080(self):
        assert format_resolution(1080) == '1080p'

    def test_720(self):
        assert format_resolution(720) == '720p'

    def test_480(self):
        assert format_resolution(480) == '480p'

    def test_low_res(self):
        assert format_resolution(360) == '480p'

    def test_zero(self):
        assert format_resolution(0) == ''

    def test_negative(self):
        assert format_resolution(-1) == ''


# ── get_shows_needing_streamdetails ─────────────────────────────────

class TestGetShowsNeedingStreamdetails:
    def _cache(self, shows_dict):
        return {'version': STREAMDETAILS_CACHE_VERSION, 'shows': shows_dict}

    def test_new_show_included(self):
        cache = self._cache({})
        result = get_shows_needing_streamdetails(cache, {100: 10})
        assert 100 in result

    def test_unchanged_show_excluded(self):
        cache = self._cache({'100': {'episode_count': 10, 'episodes': {'1': {}}}})
        result = get_shows_needing_streamdetails(cache, {100: 10})
        assert 100 not in result

    def test_count_changed_included(self):
        cache = self._cache({'100': {'episode_count': 10, 'episodes': {'1': {}}}})
        result = get_shows_needing_streamdetails(cache, {100: 15})
        assert 100 in result

    def test_empty_episodes_dict_retried(self):
        cache = self._cache({'100': {'episode_count': 10, 'episodes': {}}})
        result = get_shows_needing_streamdetails(cache, {100: 10})
        assert 100 in result

    def test_missing_episodes_key_retried(self):
        cache = self._cache({'100': {'episode_count': 10}})
        result = get_shows_needing_streamdetails(cache, {100: 10})
        assert 100 in result

    def test_pruned_show_not_in_result(self):
        cache = self._cache({'999': {'episode_count': 5, 'episodes': {'1': {}}}})
        result = get_shows_needing_streamdetails(cache, {100: 10})
        assert 999 not in result


# ── build_updated_streamdetails_cache ───────────────────────────────

class TestBuildUpdatedStreamdetailsCache:
    def _cache(self, shows_dict):
        return {'version': STREAMDETAILS_CACHE_VERSION, 'shows': shows_dict}

    def test_preserves_unchanged(self):
        old = self._cache({'100': {'episode_count': 10, 'episodes': {'1': {'duration': 500}}}})
        result = build_updated_streamdetails_cache(old, {100: 10}, {})
        assert '100' in result['shows']
        assert result['shows']['100']['episodes']['1']['duration'] == 500

    def test_adds_new_data(self):
        old = self._cache({})
        new_data = {200: {10: {'duration': 1800, 'resolution': '1080p'}}}
        result = build_updated_streamdetails_cache(old, {200: 5}, new_data)
        assert '200' in result['shows']
        assert result['shows']['200']['episodes']['10']['duration'] == 1800

    def test_prunes_removed_show(self):
        old = self._cache({'999': {'episode_count': 5, 'episodes': {}}})
        result = build_updated_streamdetails_cache(old, {100: 10}, {100: {1: {'duration': 500}}})
        assert '999' not in result['shows']

    def test_version_set(self):
        result = build_updated_streamdetails_cache(self._cache({}), {}, {})
        assert result['version'] == STREAMDETAILS_CACHE_VERSION

    def test_episode_count_set_for_new_data(self):
        new_data = {100: {1: {'duration': 500}}}
        result = build_updated_streamdetails_cache(self._cache({}), {100: 20}, new_data)
        assert result['shows']['100']['episode_count'] == 20


# ── get_episode_duration ────────────────────────────────────────────

class TestGetEpisodeDuration:
    def _cache(self, shows_dict):
        return {'version': STREAMDETAILS_CACHE_VERSION, 'shows': shows_dict}

    def test_found(self):
        cache = self._cache({'100': {'episodes': {'50': {'duration': 3633}}}})
        assert get_episode_duration(cache, 100, 50) == 3633

    def test_episode_not_found(self):
        cache = self._cache({'100': {'episodes': {'50': {'duration': 3633}}}})
        assert get_episode_duration(cache, 100, 999) == 0

    def test_show_not_found(self):
        cache = self._cache({})
        assert get_episode_duration(cache, 100, 50) == 0

    def test_empty_cache(self):
        cache = self._cache({})
        assert get_episode_duration(cache, 1, 1) == 0

    def test_missing_duration_key(self):
        cache = self._cache({'100': {'episodes': {'50': {'resolution': '1080p'}}}})
        assert get_episode_duration(cache, 100, 50) == 0
