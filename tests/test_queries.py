"""Tests for resources/lib/data/queries.py — JSON-RPC query builders."""
from resources.lib.constants import (
    EPISODE_SELECTION_UNWATCHED,
    EPISODE_SELECTION_WATCHED,
    EPISODE_SELECTION_BOTH,
)
from resources.lib.data.queries import (
    get_episode_filter,
    build_random_episodes_query,
    build_random_movies_query,
    build_player_seek_time_query,
    build_show_episodes_query,
    build_episode_details_query,
    FILTER_UNWATCHED,
)


# ── get_episode_filter ──────────────────────────────────────────────

class TestGetEpisodeFilter:
    def test_unwatched_returns_playcount_zero(self):
        f = get_episode_filter(EPISODE_SELECTION_UNWATCHED)
        assert f == {'field': 'playcount', 'operator': 'is', 'value': '0'}

    def test_watched_returns_playcount_gt_zero(self):
        f = get_episode_filter(EPISODE_SELECTION_WATCHED)
        assert f == {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'}

    def test_both_returns_none(self):
        assert get_episode_filter(EPISODE_SELECTION_BOTH) is None

    def test_unknown_mode_returns_none(self):
        assert get_episode_filter(999) is None

    def test_returns_copy_not_original(self):
        f = get_episode_filter(EPISODE_SELECTION_UNWATCHED)
        assert f is not FILTER_UNWATCHED
        f['extra'] = 'x'
        assert 'extra' not in FILTER_UNWATCHED


# ── build_random_episodes_query ──────────────────────────────────────

class TestBuildRandomEpisodesQuery:
    def test_basic_structure(self):
        q = build_random_episodes_query(tvshowid=42)
        assert q['method'] == 'VideoLibrary.GetEpisodes'
        assert q['params']['tvshowid'] == 42
        assert q['params']['sort'] == {'method': 'random'}

    def test_single_filter(self):
        f = get_episode_filter(EPISODE_SELECTION_UNWATCHED)
        q = build_random_episodes_query(tvshowid=1, filters=[f])
        assert q['params']['filter'] == f

    def test_multiple_filters_uses_and(self):
        f1 = {'field': 'a', 'operator': 'is', 'value': '1'}
        f2 = {'field': 'b', 'operator': 'is', 'value': '2'}
        q = build_random_episodes_query(tvshowid=1, filters=[f1, f2])
        assert q['params']['filter'] == {'and': [f1, f2]}

    def test_limit(self):
        q = build_random_episodes_query(tvshowid=1, limit=5)
        assert q['params']['limits'] == {'end': 5}

    def test_no_limit(self):
        q = build_random_episodes_query(tvshowid=1)
        assert 'limits' not in q['params']

    def test_zero_limit_excluded(self):
        q = build_random_episodes_query(tvshowid=1, limit=0)
        assert 'limits' not in q['params']

    def test_returns_fresh_dict(self):
        q1 = build_random_episodes_query(tvshowid=1)
        q2 = build_random_episodes_query(tvshowid=1)
        assert q1 is not q2
        q1['params']['tvshowid'] = 999
        assert q2['params']['tvshowid'] == 1


# ── build_random_movies_query ────────────────────────────────────────

class TestBuildRandomMoviesQuery:
    def test_basic_structure(self):
        q = build_random_movies_query()
        assert q['method'] == 'VideoLibrary.GetMovies'
        assert q['params']['sort'] == {'method': 'random'}

    def test_single_filter(self):
        f = get_episode_filter(EPISODE_SELECTION_WATCHED)
        q = build_random_movies_query(filters=[f])
        assert q['params']['filter'] == f

    def test_limit(self):
        q = build_random_movies_query(limit=3)
        assert q['params']['limits'] == {'end': 3}


# ── build_player_seek_time_query ─────────────────────────────────────

class TestBuildPlayerSeekTimeQuery:
    def test_3661_seconds(self):
        q = build_player_seek_time_query(3661)
        t = q['params']['value']['time']
        assert t == {'hours': 1, 'minutes': 1, 'seconds': 1, 'milliseconds': 0}

    def test_zero_seconds(self):
        q = build_player_seek_time_query(0)
        t = q['params']['value']['time']
        assert t == {'hours': 0, 'minutes': 0, 'seconds': 0, 'milliseconds': 0}

    def test_90_seconds(self):
        q = build_player_seek_time_query(90)
        t = q['params']['value']['time']
        assert t == {'hours': 0, 'minutes': 1, 'seconds': 30, 'milliseconds': 0}


# ── build_show_episodes_query ────────────────────────────────────────

class TestBuildShowEpisodesQuery:
    def test_tvshowid_substituted(self):
        q = build_show_episodes_query(tvshowid=123)
        assert q['params']['tvshowid'] == 123

    def test_returns_fresh_dict(self):
        q1 = build_show_episodes_query(tvshowid=1)
        q2 = build_show_episodes_query(tvshowid=1)
        assert q1 is not q2


# ── build_episode_details_query ──────────────────────────────────────

class TestBuildEpisodeDetailsQuery:
    def test_episodeid_substituted(self):
        q = build_episode_details_query(episode_id=456)
        assert q['params']['episodeid'] == 456

    def test_returns_fresh_dict(self):
        q1 = build_episode_details_query(episode_id=1)
        q2 = build_episode_details_query(episode_id=1)
        assert q1 is not q2
