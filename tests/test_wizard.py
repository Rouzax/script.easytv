"""Tests for the guided-flow wizard controller."""
from resources.lib.constants import (
    GUIDED_MODE_ASK,
    GUIDED_MODE_OFF,
    GUIDED_MODE_PRESET,
)
from resources.lib.ui.wizard import STEP_ORDER, WizardFlow


def _settings(**overrides):
    base = {
        "ignore_genre_mode": GUIDED_MODE_ASK, "genre_mode": GUIDED_MODE_ASK,
        "length_mode": GUIDED_MODE_ASK, "era_mode": GUIDED_MODE_ASK,
        "rating_mode": GUIDED_MODE_ASK, "depth_mode": GUIDED_MODE_ASK,
        "preset_ignore_genres": [], "preset_genres": [],
        "preset_length": 0, "preset_recency_years": 0,
        "preset_rating": 0, "preset_depth": 0,
        "duration_filter_enabled": False, "duration_min": 0,
        "duration_max": 0, "current_year": 2026,
    }
    base.update(overrides)
    return base


class TestStepList:
    def test_all_toggles_on_yields_full_order(self):
        flow = WizardFlow(_settings())
        assert flow.steps == STEP_ORDER

    def test_toggled_off_steps_are_absent(self):
        flow = WizardFlow(_settings(era_mode=GUIDED_MODE_OFF, rating_mode=GUIDED_MODE_OFF))
        assert flow.steps == ["ignore_genre", "genre", "length", "depth"]

    def test_all_off_is_immediately_complete(self):
        flow = WizardFlow(_settings(
            ignore_genre_mode=GUIDED_MODE_OFF, genre_mode=GUIDED_MODE_OFF, length_mode=GUIDED_MODE_OFF,
            era_mode=GUIDED_MODE_OFF, rating_mode=GUIDED_MODE_OFF, depth_mode=GUIDED_MODE_OFF))
        assert flow.is_complete


class TestNavigation:
    def test_advance_walks_to_completion(self):
        flow = WizardFlow(_settings(length_mode=GUIDED_MODE_OFF, era_mode=GUIDED_MODE_OFF,
                                    rating_mode=GUIDED_MODE_OFF, depth_mode=GUIDED_MODE_OFF))
        assert flow.current_step == "ignore_genre"
        assert flow.advance() is True
        assert flow.current_step == "genre"
        assert flow.advance() is False
        assert flow.is_complete

    def test_go_back_at_start_returns_false(self):
        flow = WizardFlow(_settings())
        assert flow.go_back() is False

    def test_go_back_returns_to_previous_step(self):
        flow = WizardFlow(_settings())
        flow.advance()
        assert flow.go_back() is True
        assert flow.current_step == "ignore_genre"

    def test_restart_keeps_answers(self):
        flow = WizardFlow(_settings())
        flow.set_answer("ignore_genre", ["Horror"])
        while not flow.is_complete:
            flow.advance()
        flow.restart()
        assert flow.current_step == "ignore_genre"
        assert flow.get_answers()["ignore_genre"] == ["Horror"]


class TestBuildFilterConfig:
    def test_answers_map_to_config(self):
        flow = WizardFlow(_settings())
        flow.set_answer("ignore_genre", ["Horror"])
        flow.set_answer("genre", ["Comedy"])
        flow.set_answer("length", {"min": 0, "max": 30})
        flow.set_answer("era", {"from": 2010, "to": 2019})
        flow.set_answer("rating", 8.0)
        flow.set_answer("depth", 10)
        cfg = flow.build_filter_config()
        assert cfg.ignore_genres == ["Horror"]
        assert cfg.genres == ["Comedy"]
        assert (cfg.duration_min, cfg.duration_max) == (0, 30)
        assert (cfg.year_from, cfg.year_to) == (2010, 2019)
        assert cfg.min_rating == 8.0
        assert cfg.min_eligible_episodes == 10

    def test_no_answers_yields_default_config(self):
        cfg = WizardFlow(_settings()).build_filter_config()
        assert cfg.ignore_genres is None
        assert cfg.genres is None
        assert (cfg.duration_min, cfg.duration_max) == (0, 0)


class TestDurationResolution:
    def test_length_answer_overrides_settings_range(self):
        flow = WizardFlow(_settings(duration_filter_enabled=True,
                                    duration_min=40, duration_max=60))
        flow.set_answer("length", {"min": 0, "max": 30})
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (0, 30)

    def test_no_preference_falls_back_to_settings_range(self):
        flow = WizardFlow(_settings(duration_filter_enabled=True,
                                    duration_min=40, duration_max=60))
        flow.set_answer("length", {"min": 0, "max": 0})
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (40, 60)

    def test_off_length_keeps_settings_duration_fallback(self):
        flow = WizardFlow(_settings(length_mode=GUIDED_MODE_OFF,
                                    duration_filter_enabled=True,
                                    duration_min=20, duration_max=45))
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (20, 45)

    def test_settings_filter_disabled_means_no_duration_filter(self):
        flow = WizardFlow(_settings())
        flow.set_answer("length", {"min": 0, "max": 0})
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (0, 0)


class TestPartialConfig:
    def test_partial_masks_answers_from_current_step_onward(self):
        flow = WizardFlow(_settings())
        flow.load_last_answers({"ignore_genre": ["Horror"],
                                "genre": ["Comedy"], "rating": 8.0})
        flow.advance()  # ignore_genre answered conceptually; now at "genre"
        cfg = flow.build_partial_filter_config()
        assert cfg.ignore_genres == ["Horror"]
        assert cfg.genres is None       # current step: masked
        assert cfg.min_rating == 0.0    # future step: masked

    def test_partial_does_not_lose_answers(self):
        flow = WizardFlow(_settings())
        flow.load_last_answers({"genre": ["Comedy"]})
        flow.build_partial_filter_config()
        assert flow.get_answers()["genre"] == ["Comedy"]


class TestLoadLastAnswers:
    def test_preloaded_answers_reach_final_config(self):
        flow = WizardFlow(_settings())
        flow.load_last_answers({"depth": 3})
        assert flow.build_filter_config().min_eligible_episodes == 3

    def test_unknown_keys_are_ignored(self):
        flow = WizardFlow(_settings())
        flow.load_last_answers({"bogus": 1, "genre": ["Comedy"]})
        assert flow.build_filter_config().genres == ["Comedy"]
        assert "bogus" not in flow.get_answers()

    def test_disabled_step_answer_does_not_reach_filter_config(self):
        """A saved rating answer for a toggled-off question must not
        leak into the config; rating_mode=GUIDED_MODE_OFF means "no rating filter",
        not "whatever was last picked"."""
        flow = WizardFlow(_settings(rating_mode=GUIDED_MODE_OFF))
        flow.load_last_answers({"rating": 8.0})
        assert "rating" not in flow.get_answers()
        assert flow.build_filter_config().min_rating == 0.0

    def test_disabled_length_step_leaves_settings_duration_fallback_intact(self):
        """length_mode=GUIDED_MODE_OFF must fall back to the settings duration
        range even when a stale length answer is on disk."""
        flow = WizardFlow(_settings(length_mode=GUIDED_MODE_OFF,
                                    duration_filter_enabled=True,
                                    duration_min=20, duration_max=45))
        flow.load_last_answers({"length": {"min": 0, "max": 30}})
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (20, 45)


class TestFormatCount:
    def test_with_counts(self):
        from resources.lib.ui.wizard import _fmt_count
        assert _fmt_count("Comedy", 12, True) == "Comedy (12)"

    def test_without_counts(self):
        from resources.lib.ui.wizard import _fmt_count
        assert _fmt_count("Comedy", 12, False) == "Comedy"


class TestGenreCounts:
    def test_counts_shows_containing_each_genre(self):
        from resources.lib.ui.wizard import _genre_counts
        pool = [{"genre": ["Comedy"]}, {"genre": ["Comedy", "Drama"]},
                {"genre": ["Drama"]}]
        assert _genre_counts(["Comedy", "Drama", "Horror"], pool) == {
            "Comedy": 2, "Drama": 2, "Horror": 0}

    def test_ignore_step_counts_shows_remaining_if_ignored(self):
        """Ignore Genres counts must mean "shows remaining if chosen",
        like every other step's counts: len(pool) minus the shows that
        have the genre, not the having-genre count itself."""
        from resources.lib.ui.wizard import _ignore_genre_counts
        pool = [{"genre": ["Comedy"]}, {"genre": ["Comedy", "Drama"]},
                {"genre": ["Drama"]}]
        assert _ignore_genre_counts(["Comedy", "Drama", "Horror"], pool) == {
            "Comedy": 1, "Drama": 1, "Horror": 3}


class TestLengthPreselect:
    def test_no_saved_answer_yields_no_preselect(self):
        from resources.lib.ui.wizard import _length_preselect
        assert _length_preselect(None) is None

    def test_bucket_match_returns_its_index(self):
        from resources.lib.ui.wizard import _length_preselect
        assert _length_preselect({"min": 30, "max": 45}) == 1

    def test_no_preference_answer_returns_last_index(self):
        from resources.lib.ui.wizard import _length_preselect
        assert _length_preselect({"min": 0, "max": 0}) == 3

    def test_unmatched_answer_degrades_to_no_preference(self):
        from resources.lib.ui.wizard import _length_preselect
        assert _length_preselect({"min": 5, "max": 12}) == 3


class TestEraPreselect:
    def test_no_saved_answer_yields_no_preselect(self):
        from resources.lib.ui.wizard import _era_preselect
        assert _era_preselect(None, [], 2021) is None

    def test_recent_match_returns_index_zero(self):
        from resources.lib.ui.wizard import _era_preselect
        buckets = [(2020, 5, "2020s"), (2010, 3, "2010s")]
        assert _era_preselect({"from": 2021, "to": 0}, buckets, 2021) == 0

    def test_decade_match_returns_its_index(self):
        from resources.lib.ui.wizard import _era_preselect
        buckets = [(2020, 5, "2020s"), (2010, 3, "2010s")]
        assert _era_preselect({"from": 2010, "to": 2019}, buckets, 2021) == 2

    def test_no_preference_answer_returns_last_index(self):
        from resources.lib.ui.wizard import _era_preselect
        buckets = [(2020, 5, "2020s"), (2010, 3, "2010s")]
        assert _era_preselect({"from": 0, "to": 0}, buckets, 2021) == 3

    def test_decade_absent_from_current_buckets_yields_no_preselect(self):
        """The decade list is pool-dependent: a saved decade no longer
        present must not be guessed at as "No preference"."""
        from resources.lib.ui.wizard import _era_preselect
        buckets = [(2020, 5, "2020s")]
        assert _era_preselect({"from": 2010, "to": 2019}, buckets, 2021) is None


class TestValueBucketPreselect:
    def test_no_saved_answer_yields_no_preselect(self):
        from resources.lib.ui.wizard import _value_bucket_preselect
        assert _value_bucket_preselect(None, [(7.0, 1), (8.0, 2)]) is None

    def test_zero_saved_answer_returns_any_index(self):
        from resources.lib.ui.wizard import _value_bucket_preselect
        assert _value_bucket_preselect(0, [(7.0, 1), (8.0, 2)]) == 0

    def test_bucket_match_returns_its_index(self):
        from resources.lib.ui.wizard import _value_bucket_preselect
        assert _value_bucket_preselect(8.0, [(7.0, 1), (8.0, 2)]) == 2

    def test_unmatched_answer_degrades_to_any_index(self):
        from resources.lib.ui.wizard import _value_bucket_preselect
        assert _value_bucket_preselect(9.5, [(7.0, 1), (8.0, 2)]) == 0


class TestPresetMode:
    def test_preset_steps_are_not_asked(self):
        flow = WizardFlow(_settings(genre_mode=GUIDED_MODE_PRESET,
                                    rating_mode=GUIDED_MODE_OFF))
        assert flow.steps == ["ignore_genre", "length", "era", "depth"]

    def test_preset_genres_reach_config(self):
        flow = WizardFlow(_settings(genre_mode=GUIDED_MODE_PRESET,
                                    preset_genres=["Comedy", "Drama"]))
        cfg = flow.build_filter_config()
        assert cfg.genres == ["Comedy", "Drama"]

    def test_preset_ignore_genres_reach_config(self):
        flow = WizardFlow(_settings(ignore_genre_mode=GUIDED_MODE_PRESET,
                                    preset_ignore_genres=["Horror"]))
        assert flow.build_filter_config().ignore_genres == ["Horror"]

    def test_preset_length_overrides_settings_duration(self):
        flow = WizardFlow(_settings(length_mode=GUIDED_MODE_PRESET,
                                    preset_length=1,
                                    duration_filter_enabled=True,
                                    duration_min=40, duration_max=60))
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (0, 30)

    def test_preset_length_none_falls_back_to_settings(self):
        flow = WizardFlow(_settings(length_mode=GUIDED_MODE_PRESET,
                                    preset_length=0,
                                    duration_filter_enabled=True,
                                    duration_min=40, duration_max=60))
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (40, 60)

    def test_preset_era_recency(self):
        flow = WizardFlow(_settings(era_mode=GUIDED_MODE_PRESET,
                                    preset_recency_years=5,
                                    current_year=2026))
        cfg = flow.build_filter_config()
        assert (cfg.year_from, cfg.year_to) == (2021, 0)

    def test_preset_rating_and_depth(self):
        flow = WizardFlow(_settings(rating_mode=GUIDED_MODE_PRESET,
                                    preset_rating=2,
                                    depth_mode=GUIDED_MODE_PRESET,
                                    preset_depth=1))
        cfg = flow.build_filter_config()
        assert cfg.min_rating == 8.0
        assert cfg.min_eligible_episodes == 3

    def test_empty_preset_applies_nothing(self):
        flow = WizardFlow(_settings(genre_mode=GUIDED_MODE_PRESET,
                                    preset_genres=[]))
        assert flow.build_filter_config().genres is None


class TestOffMode:
    def test_off_length_keeps_settings_duration_fallback(self):
        flow = WizardFlow(_settings(length_mode=GUIDED_MODE_OFF,
                                    duration_filter_enabled=True,
                                    duration_min=20, duration_max=45))
        cfg = flow.build_filter_config()
        assert (cfg.duration_min, cfg.duration_max) == (20, 45)

    def test_off_applies_no_other_filters(self):
        flow = WizardFlow(_settings(
            ignore_genre_mode=GUIDED_MODE_OFF, genre_mode=GUIDED_MODE_OFF,
            era_mode=GUIDED_MODE_OFF, rating_mode=GUIDED_MODE_OFF,
            depth_mode=GUIDED_MODE_OFF,
            preset_genres=["Comedy"], preset_rating=2))
        cfg = flow.build_filter_config()
        assert cfg.genres is None
        assert cfg.min_rating == 0.0


class TestPresetAnswer:
    def test_answer_shapes(self):
        flow = WizardFlow(_settings(
            preset_genres=["Comedy"], preset_ignore_genres=["Horror"],
            preset_length=3, preset_recency_years=10,
            preset_rating=1, preset_depth=2, current_year=2026))
        assert flow.preset_answer("genre") == ["Comedy"]
        assert flow.preset_answer("ignore_genre") == ["Horror"]
        assert flow.preset_answer("length") == {"min": 45, "max": 0}
        assert flow.preset_answer("era") == {"from": 2016, "to": 0}
        assert flow.preset_answer("rating") == 7.0
        assert flow.preset_answer("depth") == 10

    def test_no_preset_returns_none(self):
        flow = WizardFlow(_settings())
        for step in STEP_ORDER:
            assert flow.preset_answer(step) is None
