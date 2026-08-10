"""Tests for resources/lib/playback/playlist_session.py — session logic."""
import random

from resources.lib.playback.playlist_session import (
    PlaylistSession,
    calculate_movie_target,
    select_next_candidate,
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


# ── select_next_candidate ────────────────────────────────────────────

def _run_selection(n_shows, movie_target, length, trials, seed=1234):
    """Simulate the playlist build loop and record where movies land.

    Mirrors the real loops: shows rotate to the back after use, movies are
    one-shot and removed. Returns a list of per-trial 1-based positions for
    every movie that made it into the playlist.
    """
    random.seed(seed)
    show_target = length - movie_target
    positions = []
    for _ in range(trials):
        candidates = (
            ['t{0}'.format(i) for i in range(n_shows)] +
            ['m{0}'.format(i) for i in range(movie_target)]
        )
        random.shuffle(candidates)
        movies_added = shows_added = 0
        for slot in range(1, length + 1):
            picked = select_next_candidate(
                candidates, None,
                movie_target - movies_added,
                show_target - shows_added,
            )
            if picked is None:
                break
            if picked[0] == 'm':
                movies_added += 1
                candidates.remove(picked)
                positions.append(slot)
            else:
                shows_added += 1
                candidates.remove(picked)
                candidates.append(picked)
    return positions


class TestSelectNextCandidate:
    def test_returns_none_for_empty_list(self):
        assert select_next_candidate([], None, 1, 19) is None

    def test_picks_movie_when_only_movie_budget_remains(self):
        assert select_next_candidate(['t1', 't2', 'm9'], None, 1, 0) == 'm9'

    def test_picks_tv_when_no_movie_budget_remains(self):
        assert select_next_candidate(['m9', 't1'], None, 0, 5) == 't1'

    def test_roll_below_movie_share_picks_movie(self):
        # 1 movie of 20 remaining slots -> movie share is 0.05
        assert select_next_candidate(['t1', 't2', 'm9'], None, 1, 19, rand=0.04) == 'm9'

    def test_roll_above_movie_share_picks_tv(self):
        assert select_next_candidate(['t1', 't2', 'm9'], None, 1, 19, rand=0.06) == 't1'

    def test_falls_back_to_other_type_when_desired_type_absent(self):
        # Roll wants a movie, but no movies are left in the pool
        assert select_next_candidate(['t1', 't2'], None, 5, 5, rand=0.0) == 't1'

    def test_partial_at_front_wins_over_the_mix_roll(self):
        # Roll would pick TV, but the front candidate is a prioritised partial
        picked = select_next_candidate(
            ['m9', 't1', 't2'], {'m9'}, 1, 19, rand=0.99
        )
        assert picked == 'm9'

    def test_partial_at_front_ignored_when_its_budget_is_spent(self):
        picked = select_next_candidate(
            ['m9', 't1', 't2'], {'m9'}, 0, 19, rand=0.99
        )
        assert picked == 't1'


class TestMovieDistribution:
    """Regression: movies must be mixed through the playlist, not appended.

    The pool holds every eligible show but only movie_target movies, so
    selecting by position in the shuffled pool pushed movies to the tail.
    """

    def test_single_movie_is_not_always_last(self):
        positions = _run_selection(n_shows=120, movie_target=1, length=20, trials=400)
        assert len(positions) == 400
        last_slot_share = positions.count(20) / len(positions)
        assert last_slot_share < 0.20, (
            "movie landed in the final slot {0:.0%} of the time".format(last_slot_share)
        )

    def test_single_movie_reaches_the_first_half(self):
        positions = _run_selection(n_shows=120, movie_target=1, length=20, trials=400)
        first_half_share = sum(1 for p in positions if p <= 10) / len(positions)
        assert 0.3 < first_half_share < 0.7

    def test_half_movies_are_not_all_in_the_back_half(self):
        positions = _run_selection(n_shows=120, movie_target=10, length=20, trials=200)
        first_half_share = sum(1 for p in positions if p <= 10) / len(positions)
        assert first_half_share > 0.35

    def test_movie_target_is_still_respected_exactly(self):
        positions = _run_selection(n_shows=120, movie_target=10, length=20, trials=200)
        assert len(positions) == 10 * 200
