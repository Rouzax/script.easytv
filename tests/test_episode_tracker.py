"""Tests for episode tracker property constants."""
from resources.lib.service.episode_tracker import (
    EPISODE_PROPERTIES,
    PROP_DURATION,
    PROP_EP_RUNTIME,
)


class TestEpRuntimeProperty:
    def test_ep_runtime_constant_exists(self):
        assert PROP_EP_RUNTIME == "EpRuntime"

    def test_ep_runtime_in_episode_properties(self):
        assert PROP_EP_RUNTIME in EPISODE_PROPERTIES

    def test_duration_not_in_episode_properties(self):
        """Median duration is show-level, must NOT transition with episodes."""
        assert PROP_DURATION not in EPISODE_PROPERTIES
