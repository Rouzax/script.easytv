"""Tests for the guided-flow wizard controller."""
from resources.lib.ui.wizard import STEP_ORDER, WizardFlow


def _settings(**overrides):
    base = {
        "ask_ignore_genre": True, "ask_genre": True, "ask_length": True,
        "ask_era": True, "ask_rating": True, "ask_depth": True,
        "duration_filter_enabled": False, "duration_min": 0,
        "duration_max": 0,
    }
    base.update(overrides)
    return base


class TestStepList:
    def test_all_toggles_on_yields_full_order(self):
        flow = WizardFlow(_settings())
        assert flow.steps == STEP_ORDER

    def test_toggled_off_steps_are_absent(self):
        flow = WizardFlow(_settings(ask_era=False, ask_rating=False))
        assert flow.steps == ["ignore_genre", "genre", "length", "depth"]

    def test_all_off_is_immediately_complete(self):
        flow = WizardFlow(_settings(
            ask_ignore_genre=False, ask_genre=False, ask_length=False,
            ask_era=False, ask_rating=False, ask_depth=False))
        assert flow.is_complete


class TestNavigation:
    def test_advance_walks_to_completion(self):
        flow = WizardFlow(_settings(ask_length=False, ask_era=False,
                                    ask_rating=False, ask_depth=False))
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

    def test_untoggled_length_step_uses_settings_range(self):
        flow = WizardFlow(_settings(ask_length=False,
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
