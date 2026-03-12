"""Tests for resources/lib/playback/playlist_session.py — session logic."""
from resources.lib.playback.playlist_session import (
    calculate_movie_target,
    PlaylistSession,
)


# ── calculate_movie_target ───────────────────────────────────────────

class TestCalculateMovieTarget:
    def test_fifty_percent(self):
        assert calculate_movie_target(50, 10) == 5

    def test_zero_chance(self):
        assert calculate_movie_target(0, 10) == 0

    def test_hundred_percent(self):
        assert calculate_movie_target(100, 10) == 10

    def test_rounding(self):
        # 25% of 10 = 2.5, rounds to 2... but max(int(round(2.5)), 1) = max(2, 1) = 2
        assert calculate_movie_target(25, 10) == 2

    def test_small_chance_minimum_one(self):
        # 1% of 10 = 0.1, rounds to 0, but max(0, 1) = 1
        assert calculate_movie_target(1, 10) == 1

    def test_negative_chance(self):
        assert calculate_movie_target(-5, 10) == 0


# ── _deserialize_shows_state ─────────────────────────────────────────

class TestDeserializeShowsState:
    def test_string_keys_to_int(self):
        state = {"123": {"watched_used": []}, "456": {"watched_used": [1, 2]}}
        result = PlaylistSession._deserialize_shows_state(state)
        assert 123 in result
        assert 456 in result

    def test_empty_dict(self):
        assert PlaylistSession._deserialize_shows_state({}) == {}

    def test_invalid_returns_empty(self):
        assert PlaylistSession._deserialize_shows_state(None) == {}

    def test_non_numeric_key_returns_empty(self):
        assert PlaylistSession._deserialize_shows_state({"abc": {}}) == {}


# ── _deserialize_partial_map ─────────────────────────────────────────

class TestDeserializePartialMap:
    def test_string_to_int(self):
        data = {"123": "456", "789": "101"}
        result = PlaylistSession._deserialize_partial_map(data)
        assert result == {123: 456, 789: 101}

    def test_none_returns_empty(self):
        assert PlaylistSession._deserialize_partial_map(None) == {}

    def test_empty_dict(self):
        assert PlaylistSession._deserialize_partial_map({}) == {}

    def test_non_dict_returns_empty(self):
        assert PlaylistSession._deserialize_partial_map([1, 2, 3]) == {}

    def test_invalid_values_return_empty(self):
        assert PlaylistSession._deserialize_partial_map({"abc": "def"}) == {}
