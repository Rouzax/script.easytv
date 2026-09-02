#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV Playlist Session - Lazy Queue State Management.

Manages the state for "Both" mode playlists where on-deck episodes should
progress as content is watched. Instead of building the full playlist upfront,
this maintains a buffer and replenishes as episodes complete.

The session state is stored in a window property (JSON serialized) so it
persists across playback monitor callbacks but is ephemeral - it resets
when Kodi restarts or the playlist is stopped.

Logging:
    Logger: 'playback' (via get_logger)
    Key events:
        - session.create (DEBUG): New lazy queue session started
        - session.save (DEBUG): Session state saved
        - session.load (DEBUG): Session state loaded
        - session.clear (DEBUG): Session state cleared
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

import xbmcgui

from resources.lib.constants import (
    EPISODE_SELECTION_WATCHED,
    KODI_HOME_WINDOW_ID,
    LAZY_QUEUE_BUFFER_SIZE,
    MOVIE_CANDIDATE_PREFIX,
    PROP_LAZY_QUEUE_SESSION,
    TV_CANDIDATE_PREFIX,
)
from resources.lib.data.queries import (
    build_random_episodes_query,
    get_episode_filter,
)
from resources.lib.utils import get_logger, json_query, log_timing

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('playback')
    return _log


# Shared window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)


def calculate_movie_target(movie_chance: int, length: int) -> int:
    """Calculate target number of movies for a playlist.

    Args:
        movie_chance: Percentage of playlist that should be movies (0-100).
        length: Total playlist length.

    Returns:
        Target number of movies. 0 if movie_chance is 0.
    """
    if movie_chance <= 0:
        return 0
    if movie_chance >= 100:
        return length
    return max(int(round(length * movie_chance / 100.0)), 1)


def select_next_candidate(
    candidate_list: List[str],
    partial_candidates: Optional[Set[str]],
    movies_remaining: int,
    shows_remaining: int,
    rand: Optional[float] = None,
    uniform: bool = False
) -> Optional[str]:
    """Choose which candidate to attempt next, mixing movies through the playlist.

    The candidate pool holds every eligible show but only `movie_target`
    movies, so picking whichever candidate sits at the front of the shuffled
    pool draws movies far below their configured share and leaves the movie
    budget to be spent on the final slots. Instead, the *type* is rolled per
    slot against the remaining budget (a movie is picked with probability
    movies_remaining / (movies_remaining + shows_remaining)), which spreads
    movies evenly across the playlist while still hitting the exact target.

    Prioritised partials keep their front-of-playlist position: when the
    front candidate is a partial and its type still has budget, it is served
    before the roll applies.

    Args:
        candidate_list: Remaining candidates like ['t123', 'm456'], in
            priority order (partials first, then shuffled).
        partial_candidates: Candidate tags that were prioritised as
            in-progress items, or None when partials are disabled.
        movies_remaining: Movie slots left in the budget.
        shows_remaining: TV slots left in the budget.
        rand: Optional roll in [0, 1) for deterministic tests. Defaults to
            random.random().
        uniform: Draw the slot from all eligible candidates instead of taking
            the first. The default takes the front of the pre-shuffled list,
            which combined with rotating a used show to the back spreads
            repeats out: a show only recurs once every other one has had a
            turn. Uniform lets a show recur at any time, including back to
            back.

    Returns:
        The candidate tag to attempt, or None if the pool is empty. The
        caller still handles selection failures (exhausted show, used movie).
    """
    if not candidate_list:
        return None

    movies_left = max(0, movies_remaining)
    shows_left = max(0, shows_remaining)

    # Partials keep front-of-playlist priority while their type has budget
    # (or when nothing of the other type is left to defer to)
    front = candidate_list[0]
    if partial_candidates and front in partial_candidates:
        if front[:1] == MOVIE_CANDIDATE_PREFIX:
            if movies_left > 0 or not any(
                c[:1] == TV_CANDIDATE_PREFIX for c in candidate_list
            ):
                return front
        elif front[:1] == TV_CANDIDATE_PREFIX:
            if shows_left > 0 or not any(
                c[:1] == MOVIE_CANDIDATE_PREFIX for c in candidate_list
            ):
                return front

    # Roll the type for this slot against the remaining budget
    budget = movies_left + shows_left
    want_movie = budget > 0 and (random.random() if rand is None else rand) < movies_left / budget

    wanted = MOVIE_CANDIDATE_PREFIX if want_movie else TV_CANDIDATE_PREFIX
    fallback = TV_CANDIDATE_PREFIX if want_movie else MOVIE_CANDIDATE_PREFIX

    for prefix in (wanted, fallback):
        matching = [c for c in candidate_list if c[:1] == prefix]
        if matching:
            return random.choice(matching) if uniform else matching[0]

    # Only unknown-type entries left - hand the front one back so the caller
    # logs and discards it
    return front


class PlaylistSession:
    """
    Manages lazy queue state for Both mode playlists.
    
    This class tracks:
    - The configuration used to build the playlist
    - Which shows/movies are available (candidate list)
    - Per-show state (current on-deck episode, watched episodes used)
    - Progress toward target playlist length
    
    State is persisted to a window property as JSON, allowing the playback
    monitor to load and update the session as episodes complete.
    
    Attributes:
        active: Whether the session is active
        config: RandomPlaylistConfig as a dict
        population: Show population filter dict
        random_order_shows: List of show IDs configured for random order
        target_length: Target number of items to add to playlist
        items_added: Number of items added so far
        candidate_list: List of candidates like ['t123', 'm456']
        shows_state: Per-show state with on-deck and watched tracking
        movies_used: List of movie IDs already used
        partial_episode_map: Map of show_id → episode_id for shows with
            genuinely in-progress episodes. Used for first-encounter serving.
        partial_candidates: Set of candidate tags prioritised as in-progress
            items, which keep front-of-playlist priority over the mix roll.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        population: Dict[str, Any],
        random_order_shows: List[int],
        candidate_list: List[str],
        target_length: int,
        items_added: int = 0,
        shows_state: Optional[Dict[int, Dict[str, Any]]] = None,
        movies_used: Optional[List[int]] = None,
        partial_episode_map: Optional[Dict[int, int]] = None,
        partial_candidates: Optional[List[str]] = None
    ) -> None:
        """
        Initialize a PlaylistSession.

        Args:
            config: RandomPlaylistConfig as a dict (serialized)
            population: Show population filter dict
            random_order_shows: List of show IDs with random episode order
            candidate_list: List of candidates like ['t123', 'm456']
            target_length: Target number of items to add
            items_added: Items already added to playlist
            shows_state: Per-show tracking state
            movies_used: Movie IDs already used
            partial_episode_map: Optional map of show_id → episode_id for
                shows with genuinely in-progress episodes
            partial_candidates: Optional candidate tags that were prioritised
                as in-progress items, so they keep front-of-playlist priority
                over the movie/TV mix roll
        """
        self.active = True
        self.config = config
        self.population = population
        self.random_order_shows = random_order_shows
        self.target_length = target_length
        self.items_added = items_added
        self.candidate_list = candidate_list
        self.shows_state = shows_state if shows_state is not None else {}
        self.movies_used = movies_used if movies_used is not None else []
        self.partial_episode_map = partial_episode_map or {}
        self.partial_candidates = set(partial_candidates or [])

    @classmethod
    def create(
        cls,
        config: Dict[str, Any],
        population: Dict[str, Any],
        random_order_shows: List[int],
        candidate_list: List[str],
        target_length: int,
        partial_episode_map: Optional[Dict[int, int]] = None,
        partial_candidates: Optional[List[str]] = None
    ) -> 'PlaylistSession':
        """
        Create a new playlist session.

        This is the primary factory method for starting a new Both mode
        lazy queue session. It initializes all state and saves to the
        window property.

        Args:
            config: RandomPlaylistConfig as a dict (serialized)
            population: Show population filter dict
            random_order_shows: List of show IDs with random episode order
            candidate_list: List of candidates like ['t123', 'm456']
            target_length: Target number of items to add
            partial_episode_map: Optional map of show_id → episode_id for
                shows with genuinely in-progress episodes
            partial_candidates: Optional candidate tags prioritised as
                in-progress items

        Returns:
            A new PlaylistSession instance
        """
        log = _get_log()

        session = cls(
            config=config,
            population=population,
            random_order_shows=random_order_shows,
            candidate_list=candidate_list,
            target_length=target_length,
            items_added=0,
            shows_state={},
            movies_used=[],
            partial_episode_map=partial_episode_map,
            partial_candidates=partial_candidates
        )
        
        session.save()
        
        log.debug("Lazy queue session created",
                  event="session.create",
                  target_length=target_length,
                  candidates=len(candidate_list))
        
        return session
    
    @classmethod
    def load(cls) -> Optional['PlaylistSession']:
        """
        Load an existing session from the window property.
        
        Returns:
            PlaylistSession if active session exists, None otherwise
        """
        log = _get_log()
        
        data_json = WINDOW.getProperty(PROP_LAZY_QUEUE_SESSION)
        if not data_json:
            return None
        
        try:
            data = json.loads(data_json)
        except json.JSONDecodeError as e:
            log.warning("Failed to parse lazy queue session",
                        event="session.load_fail",
                        error=str(e))
            return None
        
        # Check if session is marked active
        if not data.get('active', False):
            return None
        
        # Reconstruct the session from stored data
        session = cls(
            config=data.get('config', {}),
            population=data.get('population', {}),
            random_order_shows=data.get('random_order_shows', []),
            candidate_list=data.get('candidate_list', []),
            target_length=data.get('target_length', 10),
            items_added=data.get('items_added', 0),
            shows_state=cls._deserialize_shows_state(data.get('shows_state', {})),
            movies_used=data.get('movies_used', []),
            partial_episode_map=cls._deserialize_partial_map(
                data.get('partial_episode_map', {})
            ),
            partial_candidates=data.get('partial_candidates', [])
        )
        
        log.debug("Lazy queue session loaded",
                  event="session.load",
                  items_added=session.items_added,
                  target_length=session.target_length,
                  remaining=session.items_remaining)
        
        return session
    
    @staticmethod
    def _deserialize_shows_state(state: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """
        Deserialize shows_state from JSON (string keys to int keys).

        JSON serialization converts int keys to strings, so we need to
        convert them back when loading.

        Args:
            state: The shows_state dict with string keys

        Returns:
            Shows state dict with integer show_id keys, empty dict on error.
        """
        try:
            return {int(k): v for k, v in state.items()}
        except (ValueError, TypeError, AttributeError):
            # Malformed data - return empty state
            return {}

    @staticmethod
    def _deserialize_partial_map(data: Any) -> Dict[int, int]:
        """
        Deserialize partial_episode_map from JSON (string keys/values to int).

        JSON serialization converts int keys to strings, so we need to
        convert them back when loading.

        Args:
            data: The partial_episode_map dict with string keys from JSON

        Returns:
            Dict mapping show_id (int) to episode_id (int), empty dict on error.
        """
        if not data or not isinstance(data, dict):
            return {}
        try:
            return {int(k): int(v) for k, v in data.items()}
        except (ValueError, TypeError, AttributeError):
            return {}
    
    def save(self) -> None:
        """
        Save the current session state to the window property.
        
        The state is serialized as JSON for persistence across
        playback monitor callbacks.
        """
        log = _get_log()
        
        data = {
            'active': self.active,
            'config': self.config,
            'population': self.population,
            'random_order_shows': self.random_order_shows,
            'target_length': self.target_length,
            'items_added': self.items_added,
            'candidate_list': self.candidate_list,
            'shows_state': self.shows_state,
            'movies_used': self.movies_used,
            'partial_episode_map': self.partial_episode_map,
            'partial_candidates': sorted(self.partial_candidates),
        }
        
        WINDOW.setProperty(PROP_LAZY_QUEUE_SESSION, json.dumps(data))
        
        log.debug("Lazy queue session saved",
                  event="session.save",
                  items_added=self.items_added,
                  remaining=self.items_remaining)
    
    @classmethod
    def clear(cls) -> None:
        """
        Clear any active session state.
        
        This should be called when:
        - Playlist playback is stopped
        - Playlist reaches target length
        - User starts a new playlist
        """
        log = _get_log()
        
        WINDOW.clearProperty(PROP_LAZY_QUEUE_SESSION)
        
        log.debug("Lazy queue session cleared", event="session.clear")
    
    @property
    def is_complete(self) -> bool:
        """
        Check if the session has reached its target length.
        
        Returns:
            True if items_added >= target_length
        """
        return self.items_added >= self.target_length
    
    @property
    def items_remaining(self) -> int:
        """
        Get the number of items remaining to reach target length.
        
        Returns:
            Number of items still needed (0 if complete)
        """
        remaining = self.target_length - self.items_added
        return max(0, remaining)
    
    @property
    def buffer_size(self) -> int:
        """
        Get the configured buffer size for lazy queue.
        
        Returns:
            The number of items to maintain in the playlist buffer
        """
        return LAZY_QUEUE_BUFFER_SIZE
    
    def pick_next_item(self) -> Optional[Tuple[str, int]]:
        """
        Pick the next item to add to the playlist.
        
        This is the core selection method for lazy queue. It:
        1. Checks if target length is reached
        2. Picks a candidate via select_next_candidate (partials keep front
           priority, every other slot rolls its type against the remaining
           movie/TV budget)
        3. For TV: applies Both mode ratio logic (on-deck vs watched)
        4. For Movies: checks not already used
        5. Updates state and increments items_added
        
        The key difference from batch mode is that on-deck is read FRESH
        from window properties each time. As episodes are watched, the
        service updates the on-deck, so S02E05 → S02E06 automatically.
        
        Returns:
            Tuple of ('episode', episode_id) or ('movie', movie_id),
            or None if complete or all candidates exhausted.
        """
        log = _get_log()
        
        # Check if we've reached target length
        if self.is_complete:
            log.debug("Session complete, no more items to pick",
                      event="session.pick_complete",
                      items_added=self.items_added,
                      target=self.target_length)
            return None
        
        # Budget tracking for mixed mode
        movie_chance = self.config.get('movie_chance', 25)
        movie_target = calculate_movie_target(movie_chance, self.target_length)
        movies_added_count = len(self.movies_used)
        shows_added_count = self.items_added - movies_added_count
        show_target = self.target_length - movie_target

        # Try to find a valid item from candidates
        while self.candidate_list:
            # Roll the type for this slot so movies mix through the playlist
            # instead of being spent on the final slots
            # Both mode with multiple_shows runs here rather than the batch
            # loop, so the repeat-style setting must be honoured here too.
            uniform = bool(self.config.get('multiple_shows')
                           and self.config.get('multiple_shows_uniform'))
            candidate = select_next_candidate(
                self.candidate_list,
                self.partial_candidates,
                movie_target - movies_added_count,
                show_target - shows_added_count,
                uniform=uniform
            )
            if candidate is None:
                break

            # Parse candidate - handle malformed data gracefully
            try:
                candidate_type = candidate[0]
                candidate_id = int(candidate[1:])
            except (IndexError, ValueError, TypeError):
                # Malformed candidate - remove and continue
                log.warning("Malformed candidate, skipping",
                            event="session.malformed_candidate",
                            candidate=str(candidate)[:50])
                self.candidate_list.remove(candidate)
                continue

            if candidate_type == TV_CANDIDATE_PREFIX:
                result = self._select_tv_episode(candidate_id)
                if result is not None:
                    episode_id, used_ondeck = result
                    self.items_added += 1
                    
                    # Move show to end of list for fair rotation. Skipped in
                    # uniform mode, where the draw ignores order and a repeat
                    # is meant to be possible at any time.
                    if not uniform:
                        self.candidate_list.remove(candidate)
                        self.candidate_list.append(candidate)
                    
                    log.debug("TV episode selected",
                              event="session.pick_episode",
                              show_id=candidate_id,
                              episode_id=episode_id,
                              used_ondeck=used_ondeck,
                              items_added=self.items_added)
                    
                    return ('episode', episode_id)
                else:
                    # Show exhausted - remove from candidates
                    self.candidate_list.remove(candidate)
                    log.debug("Show exhausted, removed from candidates",
                              event="session.show_exhausted",
                              show_id=candidate_id)
                    continue
            
            elif candidate_type == MOVIE_CANDIDATE_PREFIX:
                result = self._select_movie(candidate_id)
                if result is not None:
                    self.items_added += 1
                    
                    # Movies are one-shot - remove from candidates
                    self.candidate_list.remove(candidate)
                    
                    log.debug("Movie selected",
                              event="session.pick_movie",
                              movie_id=candidate_id,
                              items_added=self.items_added)
                    
                    return ('movie', candidate_id)
                else:
                    # Movie already used - remove from candidates
                    self.candidate_list.remove(candidate)
                    continue
            
            else:
                # Unknown candidate type - skip
                log.warning("Unknown candidate type",
                            event="session.unknown_candidate",
                            candidate=candidate)
                self.candidate_list.remove(candidate)
                continue
        
        # All candidates exhausted
        log.debug("All candidates exhausted",
                  event="session.exhausted",
                  items_added=self.items_added,
                  target=self.target_length)
        return None
    
    def _select_tv_episode(self, show_id: int) -> Optional[Tuple[int, bool]]:
        """
        Select a TV episode for Both mode.

        Uses ratio-based selection between on-deck (unwatched) and random
        watched episodes. The key feature is that on-deck is read FRESH
        each time - as episodes are watched, the service updates the
        window property, so on-deck naturally progresses.

        On first encounter, if the show has a genuinely in-progress episode
        in the partial_episode_map, that specific episode is served directly
        (bypassing the ratio roll). Subsequent encounters use normal logic.

        Args:
            show_id: The TV show ID

        Returns:
            Tuple of (episode_id, used_ondeck) or None if show exhausted.
            used_ondeck is True if we picked the on-deck episode.
        """
        log = _get_log()

        # Initialize show state if needed
        first_encounter = show_id not in self.shows_state
        if first_encounter:
            self.shows_state[show_id] = {
                'watched_used': [],  # Watched episode IDs already used
                'last_ondeck_id': None,  # Track last on-deck to detect progression
            }

        state = self.shows_state[show_id]

        # On first encounter, serve specific partial episode if available
        if first_encounter and show_id in self.partial_episode_map:
            episode_id = self.partial_episode_map[show_id]
            state['partial_served'] = True
            log.debug("Serving partial episode directly (lazy queue)",
                      show_id=show_id, episode_id=episode_id)
            return (episode_id, True)

        watched_used = state.get('watched_used', [])
        
        # Get CURRENT on-deck from window property (may have progressed!)
        current_ondeck_id = self._get_current_ondeck(show_id)
        
        # Check if on-deck has progressed since last pick
        last_ondeck = state.get('last_ondeck_id')
        if current_ondeck_id and current_ondeck_id != last_ondeck:
            # On-deck has progressed - it's available again!
            log.debug("On-deck progressed",
                      show_id=show_id,
                      old_ondeck=last_ondeck,
                      new_ondeck=current_ondeck_id)
        
        # Determine if on-deck is available
        ondeck_available = current_ondeck_id is not None
        
        # Get unwatched_ratio from config (default 50%)
        unwatched_ratio = self.config.get('unwatched_ratio', 50)
        
        # Roll the dice for ratio-based selection
        prefer_unwatched = random.randint(1, 100) <= unwatched_ratio
        
        if prefer_unwatched and ondeck_available:
            # Use the on-deck episode
            state['last_ondeck_id'] = current_ondeck_id
            return (current_ondeck_id, True)
        else:
            # Try to get a random watched episode
            watched_episode_id = self._fetch_watched_episode(show_id, watched_used)
            
            if watched_episode_id is not None:
                # Track that we've used this watched episode
                state['watched_used'] = watched_used + [watched_episode_id]
                return (watched_episode_id, False)
            elif ondeck_available:
                # No more watched episodes, fall back to on-deck
                state['last_ondeck_id'] = current_ondeck_id
                return (current_ondeck_id, True)
            else:
                # Show exhausted - both on-deck and watched depleted
                return None
    
    def _select_movie(self, movie_id: int) -> Optional[int]:
        """
        Select a movie for playlist addition.
        
        Movies are simpler than TV shows - they can only appear once
        per session. We just check if it's already been used.
        
        Args:
            movie_id: The movie ID
        
        Returns:
            The movie_id if available, None if already used.
        """
        if movie_id in self.movies_used:
            return None
        
        self.movies_used.append(movie_id)
        return movie_id
    
    def _get_current_ondeck(self, show_id: int) -> Optional[int]:
        """
        Get the current on-deck episode ID from window properties.
        
        This reads the CURRENT on-deck episode from the service's cached
        window properties. This is the key to lazy queue - as episodes
        are watched, the service updates these properties, so the on-deck
        naturally progresses (S02E05 → S02E06).
        
        Args:
            show_id: The TV show ID
        
        Returns:
            Episode ID of current on-deck, or None if no unwatched episodes.
        """
        episode_id_str = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
        if episode_id_str:
            try:
                return int(episode_id_str)
            except ValueError:
                return None
        return None
    
    def _fetch_watched_episode(
        self,
        show_id: int,
        exclude_ids: List[int]
    ) -> Optional[int]:
        """
        Fetch a random watched episode from a show.
        
        Queries the Kodi library for watched episodes, excluding any
        that have already been used in this session. Uses server-side
        random sorting for efficiency.
        
        Args:
            show_id: The TV show ID
            exclude_ids: List of episode IDs to exclude (already used)
        
        Returns:
            Episode ID or None if no more watched episodes available.
        """
        log = _get_log()
        
        # Get watched episode filter
        watch_filter = get_episode_filter(EPISODE_SELECTION_WATCHED)
        filters = [watch_filter] if watch_filter else []
        
        # Query with server-side random sort, get a few extras in case we need to exclude
        limit = 5 if exclude_ids else 1
        query = build_random_episodes_query(tvshowid=show_id, filters=filters, limit=limit)
        
        with log_timing(log, "fetch_watched_episode", show_id=show_id) as timer:
            result = json_query(query, True)
            timer.mark("query")
        
        if 'episodes' in result and result['episodes']:
            for ep in result['episodes']:
                episode_id = ep['episodeid']
                if exclude_ids and episode_id in exclude_ids:
                    continue
                log.debug("Watched episode fetched",
                          show_id=show_id,
                          episode_id=episode_id)
                return episode_id
        
        return None
