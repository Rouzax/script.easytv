#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV Show Population and Premiere Gate Filters.

Provides the candidate-gate functions shared by Browse Mode and the random
playlist builder: population filtering (smart playlist / user-selection /
episode-selection mode) and premiere gating (series/season premiere modes,
with an in-progress override read from window properties or Kodi's live
in-progress set). Kept in data/ rather than playback/ so callers that must
not import playback/ (such as ui/) can still gate candidates.

Logging:
    Logger: 'data' (via get_logger)
    Key events:
        - filter.step (DEBUG): Guided flow filter steps (apply_show_filters)
        - filter.apply (DEBUG): Guided flow filter result counts
        - browse.inprogress_error (WARNING): In-progress lookup failed,
          premiere override disabled
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import xbmcgui

from resources.lib.constants import (
    EPISODE_SELECTION_UNWATCHED,
    EPISODE_SELECTION_WATCHED,
    KODI_HOME_WINDOW_ID,
    PREMIERE_ONLY,
    PREMIERE_SKIP,
)
from resources.lib.data.queries import (
    build_inprogress_episodes_query,
    build_show_filter_query,
)
from resources.lib.data.shows import (
    extract_showids_from_playlist,
    fetch_shows_with_watched_episodes,
    fetch_unwatched_shows,
)
from resources.lib.utils import get_logger, json_query

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('data')
    return _log


# Shared window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)


def _is_in_progress(show_id: int, inprogress_ids: Optional[set]) -> bool:
    """Whether the show's on-deck episode carries a resume point.

    With inprogress_ids supplied the answer comes from Kodi's live in-progress
    set, which is authoritative. Without it we fall back to this box's cached
    Resume property, which a peer's partial watch can leave stale: the bookmark
    moves while the on-deck episode does not, so the cache is never invalidated.
    """
    if inprogress_ids is None:
        return WINDOW.getProperty(f"EasyTV.{show_id}.Resume") == "true"
    try:
        episode_id = int(WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID"))
    except (ValueError, TypeError):
        return False
    return episode_id in inprogress_ids


def should_include_show(
    show_id: int,
    series_premieres: int,
    season_premieres: int,
    inprogress_ids: Optional[set] = None,
) -> bool:
    """
    Decide whether a show passes the premiere filter.

    Each premiere type has three modes: SKIP (exclude), MIX_IN (normal),
    ONLY (premieres-only). When either type is ONLY the filter is in
    "only mode": non-premieres are excluded and the other selector decides
    which premiere types survive.

    Evaluates the show's on-deck episode, read from window properties.

    Args:
        show_id: The TV show ID.
        series_premieres: Mode for series premieres (SxxE01 where xx == 1).
        season_premieres: Mode for season premieres (SxxE01 where xx > 1).

    Returns:
        True if the show should appear in the list.
    """
    only_mode = (series_premieres == PREMIERE_ONLY
                 or season_premieres == PREMIERE_ONLY)

    episode_no = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeNo")
    if not episode_no or len(episode_no) < 6:
        return not only_mode
    try:
        season_num = int(episode_no[1:3])
        episode_num = int(episode_no[4:6])
    except (ValueError, IndexError):
        return not only_mode

    is_premiere = (episode_num == 1)

    # An in-progress premiere is kept even when its type is set to SKIP: the
    # user is part-way through it and needs a route back to it.
    #
    # Not in only mode, though. There the premiere type IS the list ("season
    # premieres only"), and an allowed premiere is already kept below whatever
    # its resume state is, so this override could only ever admit a premiere of
    # the type the user excluded. That leaked part-watched series premieres
    # into the season-premiere list and vice versa.
    if is_premiere and not only_mode:
        if _is_in_progress(show_id, inprogress_ids):
            return True

    if only_mode:
        if not is_premiere:
            return False
        if season_num == 1 and series_premieres == PREMIERE_SKIP:
            return False
        if season_num > 1 and season_premieres == PREMIERE_SKIP:
            return False
        return True

    if not is_premiere:
        return True
    if season_num == 1:
        return series_premieres != PREMIERE_SKIP
    return season_premieres != PREMIERE_SKIP


def fetch_inprogress_episode_ids(log) -> set:
    """Every episode in the library that carries a resume point, in one query.

    The premiere filter's in-progress override needs Kodi's truth, not this
    box's cache: a peer's partial watch moves the bookmark without moving the
    on-deck episode, so the cached Resume property is never invalidated and a
    part-watched premiere silently disappears from an in-progress list.

    Asking per show costs ~86ms each against a remote MySQL library (measured:
    16.8s for 164 shows, and JSON-RPC batching only removed 16% of that). The
    native inprogress filter answers for the whole library in ~114ms.

    Returns:
        Set of episode ids with an active resume point; empty on query failure,
        which degrades to "nothing is in progress" rather than raising.
    """
    try:
        result = json_query(build_inprogress_episodes_query())
        return {
            ep['episodeid']
            for ep in result.get('episodes', [])
            if 'episodeid' in ep
        }
    except Exception as e:
        log.warning("In-progress lookup failed, premiere override disabled",
                    event="browse.inprogress_error", error=str(e))
        return set()


def filter_shows_by_population(
    population: dict,
    sort_by: int,
    sort_reverse: bool,
    language: str,
    episode_selection: int = EPISODE_SELECTION_UNWATCHED,
    logger: Optional[StructuredLogger] = None
) -> list:
    """
    Filter shows based on population criteria and episode selection mode.

    Retrieves shows based on the episode_selection mode and optionally filters
    them based on a smart playlist or user-selected show list.

    Args:
        population: Dict with one of:
            - {'playlist': path} - Filter by smart playlist contents
            - {'usersel': [show_ids]} - Filter by user-selected shows
            - {'none': ''} - No filtering
        sort_by: Sort method (0=name, 1=last played, 2=random)
        sort_reverse: Whether to reverse sort order
        language: System language for sorting
        episode_selection: Which episodes to include:
            - 0 (UNWATCHED): Only shows with unwatched episodes
            - 1 (WATCHED): Only shows with watched episodes
            - 2 (BOTH): Shows with either unwatched or watched episodes
        logger: Optional logger instance

    Returns:
        List of [lastplayed_timestamp, showid, episode_id] for matching shows.
        For watched-only shows, episode_id will be empty (selected on-demand).
    """
    log = logger or _get_log()

    # Fetch shows based on episode selection mode
    if episode_selection == EPISODE_SELECTION_UNWATCHED:
        # Unwatched only - use service cache (fast path)
        stored_data = fetch_unwatched_shows(sort_by, sort_reverse, language)
        log.debug("Fetched shows with unwatched episodes", count=len(stored_data))

    elif episode_selection == EPISODE_SELECTION_WATCHED:
        # Watched only - query directly
        stored_data = fetch_shows_with_watched_episodes(sort_by, sort_reverse, language)
        log.debug("Fetched shows with watched episodes", count=len(stored_data))

    else:
        # Both - merge unwatched and watched show lists
        unwatched_shows = fetch_unwatched_shows(sort_by, sort_reverse, language)
        watched_shows = fetch_shows_with_watched_episodes(sort_by, sort_reverse, language)

        # Merge lists, avoiding duplicates (prefer unwatched entry as it has episode_id)
        unwatched_ids = {x[1] for x in unwatched_shows}
        watched_only = [x for x in watched_shows if x[1] not in unwatched_ids]

        stored_data = unwatched_shows + watched_only
        log.debug("Fetched shows for both mode",
                 unwatched=len(unwatched_shows),
                 watched_only=len(watched_only),
                 total=len(stored_data))

    log.debug("Processing stored show data")

    if 'playlist' in population:
        extracted_showlist = extract_showids_from_playlist(population['playlist'])
        # If playlist extraction returned empty, return empty (filter failed)
        if not extracted_showlist:
            log.debug("Playlist extraction returned no shows, returning empty")
            return []
    elif 'usersel' in population:
        extracted_showlist = population['usersel']
    else:
        extracted_showlist = None  # No filter configured

    if extracted_showlist is not None:
        stored_data_filtered = [x for x in stored_data if x[1] in extracted_showlist]
    else:
        stored_data_filtered = stored_data

    log.debug("Stored data processing complete", count=len(stored_data_filtered))

    return stored_data_filtered


def fetch_filterable_shows() -> List[Dict[str, Any]]:
    """All library shows with the properties the guided flow filters on."""
    result = json_query(build_show_filter_query())
    return result.get('tvshows', [])


@dataclass
class ShowFilterConfig:
    """Session-scoped mood filters. Field defaults mean 'no filter'."""
    ignore_genres: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    duration_min: int = 0
    duration_max: int = 0
    year_from: int = 0
    year_to: int = 0
    min_rating: float = 0.0
    min_eligible_episodes: int = 0


def eligible_episode_count(show: Dict[str, Any], episode_selection: int) -> int:
    """Episodes of this show the current episode_selection mode can pick."""
    total = int(show.get('episode', 0) or 0)
    watched = int(show.get('watchedepisodes', 0) or 0)
    if episode_selection == EPISODE_SELECTION_UNWATCHED:
        return max(total - watched, 0)
    if episode_selection == EPISODE_SELECTION_WATCHED:
        return watched
    return total


def apply_show_filters(
    shows: List[Dict[str, Any]],
    config: ShowFilterConfig,
    episode_selection: int,
    durations: Optional[Dict[int, int]] = None,
    reason: str = "final",
) -> List[Dict[str, Any]]:
    """Apply all configured mood filters to a list of show dicts.

    Args:
        shows: Show dicts from build_show_filter_query.
        config: Filter configuration; default fields apply no filter.
        episode_selection: EPISODE_SELECTION_* mode; drives the depth count.
        durations: tvshowid -> average episode seconds. A show with no
            entry (or 0) passes any duration filter: missing data must
            not silently hide shows.
        reason: "final" logs per-step detail, "cumulative_count" only
            the summary.

    Returns:
        Filtered list of show dicts.
    """
    log = _get_log()
    result = shows
    verbose = reason == "final"

    def _step(name: str) -> None:
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step=name, remaining=len(result))

    if config.ignore_genres:
        ignore = set(config.ignore_genres)
        result = [s for s in result
                  if not ignore.intersection(set(s.get('genre', [])))]
        _step("ignore_genres")

    if config.genres:
        wanted = set(config.genres)
        result = [s for s in result
                  if wanted.intersection(set(s.get('genre', [])))]
        _step("genres")

    if (config.duration_min > 0 or config.duration_max > 0) and durations:
        min_s = config.duration_min * 60
        max_s = config.duration_max * 60

        def _duration_ok(show: Dict[str, Any]) -> bool:
            avg = durations.get(show.get('tvshowid', 0), 0)
            if avg <= 0:
                return True
            if min_s and avg < min_s:
                return False
            if max_s and avg > max_s:
                return False
            return True

        result = [s for s in result if _duration_ok(s)]
        _step("duration")

    if config.year_from > 0:
        result = [s for s in result if s.get('year', 0) >= config.year_from]
        _step("year_from")
    if config.year_to > 0:
        result = [s for s in result
                  if 0 < s.get('year', 0) <= config.year_to]
        _step("year_to")

    if config.min_rating > 0:
        result = [s for s in result
                  if s.get('rating', 0.0) >= config.min_rating]
        _step("rating")

    if config.min_eligible_episodes > 0:
        result = [s for s in result
                  if eligible_episode_count(s, episode_selection)
                  >= config.min_eligible_episodes]
        _step("depth")

    log.debug("Filters applied", event="filter.apply", reason=reason,
              input_count=len(shows), result_count=len(result))
    return result


def extract_unique_genres(shows: List[Dict[str, Any]]) -> List[str]:
    """All distinct genres in the show list, sorted."""
    genres = set()
    for show in shows:
        genres.update(show.get('genre', []))
    return sorted(genres)


def extract_decade_buckets(shows: List[Dict[str, Any]]) -> List[Tuple[int, int, str]]:
    """(decade_start, count, label) tuples, newest first; year 0 skipped."""
    decades = Counter((s.get('year', 0) // 10) * 10
                      for s in shows if s.get('year', 0) > 0)
    return [(decade, count, f"{decade}s")
            for decade, count in sorted(decades.items(), reverse=True)]
