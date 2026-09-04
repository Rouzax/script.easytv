"""Guided-flow wizard controller.

Pure logic for step sequencing and answer bookkeeping. No dialogs, no settings
reads, no JSON-RPC. The driver feeds settings and records answers; the wizard
produces ShowFilterConfig. Answers are session-scoped and never written back
to addon settings.

Logging:
    Logger: 'wizard'
    Events:
    - wizard.start: User begins guided flow
    - wizard.step: User advances to next step or goes back
    - wizard.cancel: User cancels the flow
    - wizard.complete: User completes all steps
"""
from typing import Any, Dict, List, Optional

from resources.lib.data.show_filters import ShowFilterConfig
from resources.lib.utils import get_logger

log = get_logger('wizard')

STEP_ORDER = ["ignore_genre", "genre", "length", "era", "rating", "depth"]

_TOGGLE_KEYS = {
    "ignore_genre": "ask_ignore_genre",
    "genre": "ask_genre",
    "length": "ask_length",
    "era": "ask_era",
    "rating": "ask_rating",
    "depth": "ask_depth",
}


class WizardFlow:
    """Guided-flow step sequencing and answer bookkeeping.

    Pure logic: no dialogs, no settings reads, no JSON-RPC. The driver
    feeds it a settings dict and records answers; it produces the
    ShowFilterConfig. Answers are session-scoped and never written back
    to addon settings.
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        self._settings = settings
        self._answers: Dict[str, Any] = {}
        self._current_index = 0
        self.steps: List[str] = [
            step for step in STEP_ORDER
            if settings.get(_TOGGLE_KEYS[step], False)]

    @property
    def current_step_index(self) -> int:
        return self._current_index

    @property
    def current_step(self) -> Optional[str]:
        if self._current_index < len(self.steps):
            return self.steps[self._current_index]
        return None

    @property
    def is_complete(self) -> bool:
        return self._current_index >= len(self.steps)

    def advance(self) -> bool:
        self._current_index += 1
        return self._current_index < len(self.steps)

    def go_back(self) -> bool:
        if self._current_index <= 0:
            return False
        self._current_index -= 1
        return True

    def restart(self) -> None:
        """Return to the first step, keeping answers (zero-result retry)."""
        self._current_index = 0

    def set_answer(self, step: str, value: Any) -> None:
        self._answers[step] = value

    def get_answers(self) -> Dict[str, Any]:
        return dict(self._answers)

    def load_last_answers(self, answers: Dict[str, Any]) -> None:
        """Preload a previous session's answers as defaults."""
        self._answers.update(
            {k: v for k, v in answers.items() if k in STEP_ORDER})

    def build_partial_filter_config(self) -> ShowFilterConfig:
        """Config from steps before the current one, for cumulative counts.

        Preloaded answers for the current and future steps must not
        affect the counts shown for this step.
        """
        completed = set(self.steps[:self._current_index])
        saved = self._answers
        self._answers = {k: v for k, v in saved.items() if k in completed}
        try:
            return self.build_filter_config()
        finally:
            self._answers = saved

    def build_filter_config(self) -> ShowFilterConfig:
        config = ShowFilterConfig()
        config.ignore_genres = self._answers.get("ignore_genre") or None
        config.genres = self._answers.get("genre") or None

        length = self._answers.get("length") or {}
        if length.get("min") or length.get("max"):
            config.duration_min = length.get("min", 0)
            config.duration_max = length.get("max", 0)
        elif self._settings.get("duration_filter_enabled"):
            # "No preference" (and an untoggled step) fall back to the
            # settings duration filter; the mode-level filter is disabled
            # for guided runs so this is the single application point.
            config.duration_min = self._settings.get("duration_min", 0)
            config.duration_max = self._settings.get("duration_max", 0)

        era = self._answers.get("era") or {}
        config.year_from = era.get("from", 0)
        config.year_to = era.get("to", 0)
        config.min_rating = float(self._answers.get("rating", 0) or 0)
        config.min_eligible_episodes = int(self._answers.get("depth", 0) or 0)
        return config
