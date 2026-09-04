"""Guided-flow wizard controller and dialog driver.

WizardFlow is pure logic for step sequencing and answer bookkeeping: no
dialogs, no settings reads, no JSON-RPC. run_wizard drives WizardFlow through
one themed dialog per step, reading settings and show data and writing
session-scoped answers; WizardFlow produces the ShowFilterConfig that
narrows the candidate set. Answers are never written back to addon settings,
only to the wizard answers file via save_wizard_answers.

Logging:
    Logger: 'wizard'
    Events:
    - wizard.start: User begins guided flow
    - wizard.step: User advances to next step or goes back
    - wizard.cancel: User cancels the flow
    - wizard.complete: User completes all steps
    - wizard.empty_base: The pre-wizard candidate set was already empty
"""
import datetime
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from resources.lib.constants import (
    EPISODE_SELECTION_UNWATCHED,
    GUIDED_DEPTH_BUCKETS,
    GUIDED_LENGTH_BUCKETS,
    GUIDED_MODE_ASK,
    GUIDED_MODE_OFF,
    GUIDED_MODE_PRESET,
    GUIDED_RATING_BUCKETS,
    GUIDED_RECENT_YEARS,
)
from resources.lib.data.show_filters import (
    ShowFilterConfig,
    apply_show_filters,
    eligible_episode_count,
    extract_decade_buckets,
    extract_unique_genres,
    fetch_filterable_shows,
    resolve_candidate_show_ids,
)
from resources.lib.data.shows import get_show_duration
from resources.lib.data.storage import load_wizard_answers, save_wizard_answers
from resources.lib.utils import (
    get_bool_setting,
    get_int_setting,
    get_logger,
    get_setting,
    lang,
)

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger

log = get_logger('wizard')

STEP_ORDER = ["ignore_genre", "genre", "length", "era", "rating", "depth"]

_MODE_KEYS = {
    "ignore_genre": "ignore_genre_mode",
    "genre": "genre_mode",
    "length": "length_mode",
    "era": "era_mode",
    "rating": "rating_mode",
    "depth": "depth_mode",
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
            if settings.get(_MODE_KEYS[step], GUIDED_MODE_OFF) == GUIDED_MODE_ASK]

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
        """Preload a previous session's answers as defaults.

        Filters against self.steps (the enabled steps for this run), not
        STEP_ORDER: an answer saved while a question was on must not
        leak into the config once that question is toggled off, or it
        silently overrides the disabled-question fallback (e.g. the
        settings duration range) instead of leaving it alone.
        """
        self._answers.update(
            {k: v for k, v in answers.items() if k in self.steps})

    def mode(self, step: str) -> int:
        """The configured Ask/Pre-set/Skip mode for a step."""
        return self._settings.get(_MODE_KEYS[step], GUIDED_MODE_OFF)

    def preset_answer(self, step: str) -> Any:
        """The configured preset for a step, in answer shape, or None.

        Used two ways: as the silently applied answer when the step's
        mode is Pre-set, and as the pre-selected default when the step
        is asked and no remembered answer exists.
        """
        s = self._settings
        if step == "ignore_genre":
            return list(s.get("preset_ignore_genres") or []) or None
        if step == "genre":
            return list(s.get("preset_genres") or []) or None
        if step == "length":
            idx = int(s.get("preset_length", 0) or 0)
            if not 1 <= idx <= len(GUIDED_LENGTH_BUCKETS):
                return None
            lo, hi, _label = GUIDED_LENGTH_BUCKETS[idx - 1]
            return {"min": lo, "max": hi}
        if step == "era":
            years = int(s.get("preset_recency_years", 0) or 0)
            if years <= 0:
                return None
            return {"from": int(s.get("current_year", 0)) - years, "to": 0}
        if step == "rating":
            idx = int(s.get("preset_rating", 0) or 0)
            if not 1 <= idx <= len(GUIDED_RATING_BUCKETS):
                return None
            return GUIDED_RATING_BUCKETS[idx - 1][0]
        if step == "depth":
            idx = int(s.get("preset_depth", 0) or 0)
            if not 1 <= idx <= len(GUIDED_DEPTH_BUCKETS):
                return None
            return GUIDED_DEPTH_BUCKETS[idx - 1][0]
        return None

    def _effective_answer(self, step: str) -> Any:
        """Answer for config building: Ask -> recorded answer,
        Pre-set -> preset, Skip -> None."""
        step_mode = self.mode(step)
        if step_mode == GUIDED_MODE_ASK:
            return self._answers.get(step)
        if step_mode == GUIDED_MODE_PRESET:
            return self.preset_answer(step)
        return None

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
        config.ignore_genres = self._effective_answer("ignore_genre") or None
        config.genres = self._effective_answer("genre") or None

        length = self._effective_answer("length") or {}
        if length.get("min") or length.get("max"):
            config.duration_min = length.get("min", 0)
            config.duration_max = length.get("max", 0)
        elif self._settings.get("duration_filter_enabled"):
            # Ask-with-no-preference, Skip, and an empty preset all fall
            # back to the settings duration filter; the mode-level filter
            # is disabled for guided runs so this stays the single
            # application point.
            config.duration_min = self._settings.get("duration_min", 0)
            config.duration_max = self._settings.get("duration_max", 0)

        era = self._effective_answer("era") or {}
        config.year_from = era.get("from", 0)
        config.year_to = era.get("to", 0)
        config.min_rating = float(self._effective_answer("rating") or 0)
        config.min_eligible_episodes = int(self._effective_answer("depth") or 0)
        return config


@dataclass
class WizardResult:
    """What the guided flow hands back to main_entry."""
    allowed_show_ids: Set[int]


def _fmt_count(label: str, count: int, show_counts: bool) -> str:
    if show_counts:
        return f"{label} ({count})"
    return label


def _genre_counts(genres: List[str],
                   pool: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {g: 0 for g in genres}
    for show in pool:
        for g in show.get('genre', []):
            if g in counts:
                counts[g] += 1
    return counts


def _ignore_genre_counts(genres: List[str],
                         pool: List[Dict[str, Any]]) -> Dict[str, int]:
    """Shows remaining if each genre is added to the ignore list.

    Every other step's counts mean "shows remaining if you pick this",
    so the Ignore Genres counts must too: the complement of
    _genre_counts, not the having-genre count itself.
    """
    having = _genre_counts(genres, pool)
    return {g: len(pool) - having[g] for g in genres}


def _length_preselect(saved: Optional[Dict[str, Any]]) -> Optional[int]:
    """Option index for a remembered length answer.

    Options are GUIDED_LENGTH_BUCKETS followed by "No preference" (the
    last index). A saved {"min": 0, "max": 0}, or any answer that does
    not match a bucket exactly, degrades to "No preference" rather than
    being left unmatched.
    """
    if saved is None:
        return None
    no_preference = len(GUIDED_LENGTH_BUCKETS)
    lo, hi = saved.get("min", 0), saved.get("max", 0)
    for i, (blo, bhi, _label_id) in enumerate(GUIDED_LENGTH_BUCKETS):
        if blo == lo and bhi == hi:
            return i
    return no_preference


def _era_preselect(saved: Optional[Dict[str, Any]],
                   buckets: List[Tuple[int, int, str]],
                   cutoff: int) -> Optional[int]:
    """Option index for a remembered era answer.

    Options are "Recent" (index 0), one per decade bucket, then "No
    preference" (the last index). The decade list is pool-dependent, so
    a saved decade absent from the current buckets is left unmatched
    (None) rather than guessed at with "No preference".
    """
    if saved is None:
        return None
    lo, hi = saved.get("from", 0), saved.get("to", 0)
    if lo == cutoff and hi == 0:
        return 0
    for i, (decade, _count, _label) in enumerate(buckets):
        if lo == decade and hi == decade + 9:
            return 1 + i
    if lo == 0 and hi == 0:
        return 1 + len(buckets)
    return None


def _value_bucket_preselect(saved: Optional[float],
                            buckets: List[Tuple[Any, int]]) -> Optional[int]:
    """Option index for a remembered rating/depth answer.

    Options are "Any"/"Anything" (index 0), then one per bucket. A saved
    0 means "Any"/"Anything" was chosen (buckets never start at 0); an
    unmatched non-zero answer also degrades to that index.
    """
    if saved is None:
        return None
    if not saved:
        return 0
    for i, (value, _label_id) in enumerate(buckets):
        if value == saved:
            return i + 1
    return 0


def _parse_genre_list(raw: str) -> List[str]:
    """Genre preset settings store a JSON list; anything else means none."""
    if not raw or raw == 'none':
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(g) for g in data]


def _saved_or_preset(flow: WizardFlow, step: str) -> Any:
    """Preselection source: the remembered/recorded answer wins whenever
    one EXISTS (even a falsy 'no filter' answer); the preset fills in
    only when the step has no recorded answer at all."""
    answers = flow.get_answers()
    if step in answers:
        return answers[step]
    return flow.preset_answer(step)


def _avoided_genres(flow: WizardFlow) -> Set[str]:
    """Genres to exclude from the Select Genres list.

    Mirrors the ignore_genre step's effective answer: Ask contributes
    its recorded answer (always present by the time "genre" is reached,
    since ignore_genre precedes it in STEP_ORDER), Pre-set contributes
    the configured preset even though the step is never asked, and Skip
    contributes nothing, even if a stale preset value lingers in
    settings from an earlier mode.
    """
    if flow.mode("ignore_genre") == GUIDED_MODE_OFF:
        return set()
    return set(_saved_or_preset(flow, "ignore_genre") or [])


def run_wizard(addon_id: str, population: dict, mode_choice: int,
               logger: 'StructuredLogger') -> Optional[WizardResult]:
    """Run the guided questions and return the allowed show ids.

    Returns None when the user cancels; the caller aborts the launch.
    An empty allowed set is returned as-is: the mode shows its normal
    empty-result behavior.
    """
    from resources.lib.ui.dialogs import show_confirm

    episode_selection = (
        get_int_setting('episode_selection', addon_id)
        if mode_choice == 1 else EPISODE_SELECTION_UNWATCHED)

    base_ids = resolve_candidate_show_ids(
        population, episode_selection,
        get_int_setting('premieres', addon_id),
        get_int_setting('season_premieres', addon_id),
        logger)
    if not base_ids:
        logger.info("Guided flow found no base candidates",
                    event="wizard.empty_base")
        return WizardResult(allowed_show_ids=set())

    all_shows = [s for s in fetch_filterable_shows()
                 if s.get('tvshowid') in base_ids]
    durations = {sid: get_show_duration(sid) for sid in base_ids}

    settings = {
        "ignore_genre_mode": get_int_setting('guided_ignore_genre_mode', addon_id),
        "genre_mode": get_int_setting('guided_genre_mode', addon_id),
        "length_mode": get_int_setting('guided_length_mode', addon_id),
        "era_mode": get_int_setting('guided_era_mode', addon_id),
        "rating_mode": get_int_setting('guided_rating_mode', addon_id),
        "depth_mode": get_int_setting('guided_depth_mode', addon_id),
        "preset_ignore_genres": _parse_genre_list(
            get_setting('guided_preset_ignore_genres', addon_id)),
        "preset_genres": _parse_genre_list(
            get_setting('guided_preset_genres', addon_id)),
        "preset_length": get_int_setting('guided_preset_length', addon_id),
        "preset_recency_years": get_int_setting('guided_preset_recency_years', addon_id),
        "preset_rating": get_int_setting('guided_preset_rating', addon_id),
        "preset_depth": get_int_setting('guided_preset_depth', addon_id),
        "duration_filter_enabled": get_bool_setting('duration_filter_enabled', addon_id),
        "duration_min": get_int_setting('duration_min', addon_id),
        "duration_max": get_int_setting('duration_max', addon_id),
        "current_year": datetime.datetime.now().year,
    }
    remember = get_bool_setting('guided_remember_answers', addon_id)
    show_counts = get_bool_setting('guided_show_counts', addon_id)

    flow = WizardFlow(settings)
    if remember:
        flow.load_last_answers(load_wizard_answers(addon_id))
    log.info("Guided flow started", event="wizard.start",
             steps=list(flow.steps), candidates=len(base_ids))

    while True:
        completed = _run_steps(flow, all_shows, durations,
                               episode_selection, addon_id, show_counts)
        if not completed:
            log.info("Guided flow cancelled", event="wizard.cancel")
            return None
        config = flow.build_filter_config()
        filtered = apply_show_filters(all_shows, config,
                                      episode_selection, durations)
        if filtered:
            break
        if not flow.steps:
            # Nothing was asked (every question is Pre-set or Skip):
            # _run_steps returns immediately on every retry, so the
            # confirm dialog below would loop forever with no way for
            # the user to change anything. Hand back an empty result
            # and let the mode show its normal empty-result behavior,
            # the same as an empty base candidate set.
            log.info("Guided flow complete", event="wizard.complete",
                     result_count=0, candidates=len(base_ids))
            return WizardResult(allowed_show_ids=set())
        again = show_confirm('EasyTV', lang(32788, addon_id),
                             yes_label=lang(32789, addon_id),
                             no_label=lang(32734, addon_id),
                             addon_id=addon_id)
        if not again:
            log.info("Guided flow cancelled at zero results",
                     event="wizard.cancel")
            return None
        flow.restart()

    if remember:
        save_wizard_answers(flow.get_answers(), addon_id)
    log.info("Guided flow complete", event="wizard.complete",
             result_count=len(filtered), candidates=len(base_ids))
    return WizardResult(
        allowed_show_ids={s['tvshowid'] for s in filtered})


def _run_steps(flow: WizardFlow, all_shows: List[Dict[str, Any]],
               durations: Dict[int, int], episode_selection: int,
               addon_id: str, show_counts: bool) -> bool:
    """Walk the flow, one dialog per step.

    Every dialog-cancel means go_back; cancelling from the first step
    cancels the whole wizard. Returns True when the flow completed
    (possibly with zero steps configured), False on cancel.
    """
    from resources.lib.ui.dialogs import show_multi_select, show_select

    def _pool() -> List[Dict[str, Any]]:
        """Shows remaining under the answers of completed steps."""
        return apply_show_filters(
            all_shows, flow.build_partial_filter_config(),
            episode_selection, durations, reason="cumulative_count")

    def _single(heading_id: int, options: List[Tuple[str, int]],
                preselect: Optional[int] = None) -> Optional[int]:
        """One single-select step. options = (label, count). Returns the
        selected option index, or None for back/cancel."""
        items = [_fmt_count(label, count, show_counts)
                 for label, count in options]
        idx = show_select(lang(heading_id, addon_id), items,
                          addon_id=addon_id, preselected_index=preselect)
        return None if idx < 0 else idx

    while not flow.is_complete:
        step = flow.current_step
        if step is None:
            break
        pool = _pool()
        answer: Any = None

        if step in ("ignore_genre", "genre"):
            genres = extract_unique_genres(all_shows)
            if step == "genre":
                # Avoided genres make no sense to also want.
                genres = [g for g in genres if g not in _avoided_genres(flow)]
            if not genres:
                flow.set_answer(step, [])
                if not flow.advance():
                    break
                continue
            counts = (_ignore_genre_counts(genres, pool)
                     if step == "ignore_genre" else _genre_counts(genres, pool))
            items = [_fmt_count(g, counts[g], show_counts) for g in genres]
            previous = set(_saved_or_preset(flow, step) or [])
            preselected = [i for i, g in enumerate(genres) if g in previous]
            heading = 32770 if step == "ignore_genre" else 32771
            result = show_multi_select(lang(heading, addon_id), items,
                                       preselected=preselected,
                                       addon_id=addon_id)
            if result is None:
                if not flow.go_back():
                    return False
                continue
            answer = [genres[i] for i in result]

        elif step == "length":
            def _len_count(lo: int, hi: int) -> int:
                cfg = ShowFilterConfig(duration_min=lo, duration_max=hi)
                return len(apply_show_filters(
                    pool, cfg, episode_selection, durations,
                    reason="cumulative_count"))
            options = [(lang(label_id, addon_id), _len_count(lo, hi))
                       for lo, hi, label_id in GUIDED_LENGTH_BUCKETS]
            options.append((lang(32776, addon_id), len(pool)))
            saved = _saved_or_preset(flow, "length")
            preselect = _length_preselect(saved)
            idx = _single(32772, options, preselect)
            if idx is None:
                if not flow.go_back():
                    return False
                continue
            if idx < len(GUIDED_LENGTH_BUCKETS):
                lo, hi, _ = GUIDED_LENGTH_BUCKETS[idx]
                answer = {"min": lo, "max": hi}
            else:
                answer = {"min": 0, "max": 0}

        elif step == "era":
            current_year = datetime.datetime.now().year
            cutoff = current_year - GUIDED_RECENT_YEARS
            buckets = extract_decade_buckets(pool)
            recent = sum(1 for s in pool if s.get('year', 0) >= cutoff)
            options = [(lang(32780, addon_id), recent)]
            options.extend((label, count) for _, count, label in buckets)
            options.append((lang(32776, addon_id), len(pool)))
            saved = _saved_or_preset(flow, "era")
            preselect = _era_preselect(saved, buckets, cutoff)
            idx = _single(32773, options, preselect)
            if idx is None:
                if not flow.go_back():
                    return False
                continue
            if idx == 0:
                answer = {"from": cutoff, "to": 0}
            elif idx <= len(buckets):
                decade = buckets[idx - 1][0]
                answer = {"from": decade, "to": decade + 9}
            else:
                answer = {"from": 0, "to": 0}

        elif step == "rating":
            options = [(lang(32782, addon_id), len(pool))]
            for min_rating, label_id in GUIDED_RATING_BUCKETS:
                count = sum(1 for s in pool
                            if s.get('rating', 0.0) >= min_rating)
                options.append((lang(label_id, addon_id), count))
            saved = _saved_or_preset(flow, "rating")
            preselect = _value_bucket_preselect(saved, GUIDED_RATING_BUCKETS)
            idx = _single(32774, options, preselect)
            if idx is None:
                if not flow.go_back():
                    return False
                continue
            answer = 0 if idx == 0 else GUIDED_RATING_BUCKETS[idx - 1][0]

        elif step == "depth":
            options = [(lang(32785, addon_id), len(pool))]
            for min_eps, label_id in GUIDED_DEPTH_BUCKETS:
                count = sum(
                    1 for s in pool
                    if eligible_episode_count(s, episode_selection) >= min_eps)
                options.append((lang(label_id, addon_id), count))
            saved = _saved_or_preset(flow, "depth")
            preselect = _value_bucket_preselect(saved, GUIDED_DEPTH_BUCKETS)
            idx = _single(32775, options, preselect)
            if idx is None:
                if not flow.go_back():
                    return False
                continue
            answer = 0 if idx == 0 else GUIDED_DEPTH_BUCKETS[idx - 1][0]

        flow.set_answer(step, answer)
        log.debug("Guided answer recorded", event="wizard.step",
                  step=step, answer=answer, remaining=len(pool))
        if not flow.advance():
            break
    return True
