#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV Random Playlist Builder.

Builds and plays a randomized "channel surfing" playlist of TV episodes
and optionally movies. Creates an experience similar to traditional TV
where content plays continuously in random order.

Extracted from default.py as part of modularization.

Logging:
    Logger: 'playback' (via get_logger)
    Key events:
        - playlist.create (INFO): Playlist generation started
        - playlist.start (INFO): Playlist playback started
        - playlist.parse_fail (WARNING): Failed to parse episode data
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import ast
import json
import random
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

import xbmc
import xbmcgui

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    PLAYLIST_BUILD_BREAK_VALUE,
)
from resources.lib.data.queries import (
    get_clear_video_playlist_query,
    build_add_episode_query,
    build_add_movie_query,
    get_unwatched_movies_query,
    get_watched_movies_query,
    get_all_movies_query,
)
from resources.lib.data.shows import (
    find_next_episode,
    fetch_unwatched_shows,
    extract_showids_from_playlist,
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
        _log = get_logger('playback')
    return _log


# Shared window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)

# Playlist content type constants - single source of truth
CONTENT_TV_ONLY = 0
CONTENT_MIXED = 1
CONTENT_MOVIES_ONLY = 2


@dataclass
class RandomPlaylistConfig:
    """
    Configuration for the random playlist builder.
    
    Attributes:
        length: Target number of items in the playlist
        playlist_content: Content type (CONTENT_TV_ONLY=0, CONTENT_MIXED=1, CONTENT_MOVIES_ONLY=2)
        movie_selection: Which movies to include (0=unwatched, 1=watched, 2=both)
        movieweight: Ratio of movies to shows (0.0-1.0), only applies to CONTENT_MIXED
        start_partials: Whether to prioritize partially watched episodes
        premieres: Whether to include premiere episodes (S01E01)
        multiple_shows: Whether the same show can appear multiple times
        sort_by: Sort method for shows (0=name, 1=last played, 2=random)
        sort_reverse: Whether to reverse the sort order
        language: System language for sorting
    """
    length: int = 10
    playlist_content: int = CONTENT_MIXED
    movie_selection: int = 0  # 0=unwatched, 1=watched, 2=both
    movieweight: float = 0.5
    start_partials: bool = False
    premieres: bool = True
    multiple_shows: bool = False
    sort_by: int = 0
    sort_reverse: bool = False
    language: str = 'English'


def filter_shows_by_population(
    population: dict,
    sort_by: int,
    sort_reverse: bool,
    language: str,
    logger: Optional[StructuredLogger] = None
) -> list:
    """
    Filter shows based on population criteria (playlist or user selection).
    
    Retrieves all unwatched shows and optionally filters them based on
    a smart playlist or user-selected show list.
    
    Args:
        population: Dict with one of:
            - {'playlist': path} - Filter by smart playlist contents
            - {'usersel': [show_ids]} - Filter by user-selected shows
            - {'none': ''} - No filtering
        sort_by: Sort method (0=name, 1=last played, 2=random)
        sort_reverse: Whether to reverse sort order
        language: System language for sorting
        logger: Optional logger instance
    
    Returns:
        List of [lastplayed_timestamp, showid, episode_id] for matching shows.
    """
    log = logger or _get_log()
    
    stored_data = fetch_unwatched_shows(sort_by, sort_reverse, language)
    
    log.debug("Processing stored show data")
    
    if 'playlist' in population:
        extracted_showlist = extract_showids_from_playlist(population['playlist'])
    elif 'usersel' in population:
        extracted_showlist = population['usersel']
    else:
        extracted_showlist = False
    
    if extracted_showlist:
        stored_data_filtered = [x for x in stored_data if x[1] in extracted_showlist]
    else:
        stored_data_filtered = stored_data
    
    log.debug("Stored data processing complete", count=len(stored_data_filtered))
    
    return stored_data_filtered


def _fetch_movies(
    include_unwatched: bool,
    include_watched: bool,
    logger: StructuredLogger
) -> list[int]:
    """
    Fetch movie IDs based on watch status settings.
    
    Args:
        include_unwatched: Include unwatched movies
        include_watched: Include watched movies
        logger: Logger instance
    
    Returns:
        List of movie IDs, shuffled randomly.
    """
    if include_unwatched and include_watched:
        mov = json_query(get_all_movies_query(), True)
    elif include_unwatched:
        mov = json_query(get_unwatched_movies_query(), True)
    elif include_watched:
        mov = json_query(get_watched_movies_query(), True)
    else:
        return []
    
    if 'movies' in mov and mov['movies']:
        movie_list = [x['movieid'] for x in mov['movies']]
        logger.debug("Movies found", count=len(movie_list))
        if movie_list:
            random.shuffle(movie_list)
        return movie_list
    
    return []


def _find_partial_episode_start(
    candidate_list: list[str],
    logger: StructuredLogger
) -> Optional[int]:
    """
    Find the index of the most recently watched partial episode.
    
    Checks all TV show candidates for resume points and returns the
    index of the one with the most recent lastplayed timestamp.
    
    Args:
        candidate_list: List of candidate IDs (prefixed with 't' or 'm')
        logger: Logger instance
    
    Returns:
        Index into candidate_list of the partial episode to start with,
        or None if no partial episodes found.
    """
    if not candidate_list:
        return None
    
    # Get show IDs from TV candidates
    shows_with_partial_progress = [
        int(x[1:]) for x in candidate_list if x[0] == 't'
    ]
    
    if not shows_with_partial_progress:
        return None
    
    # Build batch query for episodes with resume points
    queries = []
    for showid in shows_with_partial_progress:
        if WINDOW.getProperty(f"EasyTV.{showid}.Resume") == 'true':
            temp_ep = WINDOW.getProperty(f"EasyTV.{showid}.EpisodeID")
            if temp_ep:
                queries.append({
                    "jsonrpc": "2.0",
                    "method": "VideoLibrary.GetEpisodeDetails",
                    "params": {
                        "properties": ["lastplayed", "tvshowid"],
                        "episodeid": int(temp_ep)
                    },
                    "id": "1"
                })
    
    if not queries:
        return None
    
    # Execute batch query
    xbmc_request = json.dumps(queries)
    result = xbmc.executeJSONRPC(xbmc_request)
    
    if not result:
        return None
    
    # Parse results and sort by lastplayed
    last_watched_sorted = []
    try:
        reslist = ast.literal_eval(result)
        for res in reslist:
            if 'result' in res and 'episodedetails' in res['result']:
                last_watched_sorted.append((
                    res['result']['episodedetails']['lastplayed'],
                    res['result']['episodedetails']['tvshowid']
                ))
    except (ValueError, SyntaxError):
        logger.warning("Failed to parse partial episode results", event="playlist.parse_fail")
        return None
    
    if not last_watched_sorted:
        return None
    
    last_watched_sorted.sort(reverse=True)
    
    # Find index of most recently watched show
    target_tag = 't' + str(last_watched_sorted[0][1])
    try:
        index = candidate_list.index(target_tag)
        logger.debug("Starting with partial episode", index=index)
        return index
    except ValueError:
        return None


def _process_tv_candidate(
    show_id: int,
    added_ep_dict: dict,
    candidate_list: list[str],
    random_order_shows: list[int],
    config: RandomPlaylistConfig,
    logger: StructuredLogger
) -> tuple[Optional[int], bool]:
    """
    Process a TV show candidate for playlist addition.
    
    Args:
        show_id: The TV show ID
        added_ep_dict: Dict tracking added episodes per show
        candidate_list: List of remaining candidates (modified in place)
        random_order_shows: List of show IDs with random episode order
        config: Playlist configuration
        logger: Logger instance
    
    Returns:
        Tuple of (episode_id, is_multi_episode) or (None, False) if skipped.
    """
    candidate_tag = f't{show_id}'
    
    if show_id in added_ep_dict:
        # Show already added to playlist
        logger.debug("Show already in playlist", show_id=show_id)
        
        if config.multiple_shows:
            # Find next episode for multi-episode mode
            tmp_episode_id, tmp_details = find_next_episode(
                show_id, random_order_shows,
                epid=added_ep_dict[show_id][3],
                eps=added_ep_dict[show_id][2]
            )
            
            if tmp_episode_id == 'null':
                if candidate_tag in candidate_list:
                    candidate_list.remove(candidate_tag)
                    logger.debug("Show abandoned (no next episode)", show_id=show_id)
                return None, False
            
            return int(tmp_episode_id), True
        else:
            # Not multi-episode mode, skip this show
            return None, False
    else:
        # First episode from this show
        logger.debug("Show not yet in playlist", show_id=show_id)
        
        episode_id_str = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
        if not episode_id_str:
            if candidate_tag in candidate_list:
                candidate_list.remove(candidate_tag)
            return None, False
        
        tmp_episode_id = int(episode_id_str)
        
        if not config.multiple_shows:
            # Remove from candidates if not allowing multiple
            if candidate_tag in candidate_list:
                candidate_list.remove(candidate_tag)
            logger.debug("Show abandoned (no multi-episode)", show_id=show_id)
        
        return tmp_episode_id, False


def _check_premiere_exclusion(
    show_id: int,
    candidate_list: list[str],
    config: RandomPlaylistConfig,
    logger: StructuredLogger
) -> bool:
    """
    Check if episode should be excluded due to premiere setting.
    
    Args:
        show_id: The TV show ID
        candidate_list: List of remaining candidates (modified in place)
        config: Playlist configuration
        logger: Logger instance
    
    Returns:
        True if episode should be excluded, False otherwise.
    """
    if config.premieres:
        return False
    
    episode_no = WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeNo")
    if episode_no == 's01e01':
        candidate_tag = f't{show_id}'
        if candidate_tag in candidate_list:
            candidate_list.remove(candidate_tag)
        logger.debug("Show abandoned (premiere excluded)", show_id=show_id)
        return True
    
    return False


def _update_added_dict(
    show_id: int,
    added_ep_dict: dict,
    random_order_shows: list[int],
    is_multi: bool,
    tmp_details: Optional[list],
    config: RandomPlaylistConfig
) -> None:
    """
    Update the added episodes dictionary after adding an episode.
    
    Args:
        show_id: The TV show ID
        added_ep_dict: Dict tracking added episodes (modified in place)
        random_order_shows: List of show IDs with random episode order
        is_multi: Whether this is a multi-episode add
        tmp_details: Details from find_next_episode if multi
        config: Playlist configuration
    """
    if is_multi and tmp_details:
        added_ep_dict[show_id] = [
            tmp_details[0], tmp_details[1],
            tmp_details[2], tmp_details[3]
        ]
    elif config.multiple_shows:
        # Build episode list for future multi-episode lookups
        if show_id in random_order_shows:
            ondeck = WINDOW.getProperty(f"EasyTV.{show_id}.ondeck_list")
            offdeck = WINDOW.getProperty(f"EasyTV.{show_id}.offdeck_list")
            try:
                eps_list = ast.literal_eval(ondeck) + ast.literal_eval(offdeck)
            except (ValueError, SyntaxError):
                eps_list = []
        else:
            ondeck = WINDOW.getProperty(f"EasyTV.{show_id}.ondeck_list")
            try:
                eps_list = ast.literal_eval(ondeck)
            except (ValueError, SyntaxError):
                eps_list = []
        
        added_ep_dict[show_id] = [
            WINDOW.getProperty(f"EasyTV.{show_id}.Season"),
            WINDOW.getProperty(f"EasyTV.{show_id}.Episode"),
            eps_list,
            WINDOW.getProperty(f"EasyTV.{show_id}.EpisodeID")
        ]
    else:
        added_ep_dict[show_id] = ''


def build_random_playlist(
    population: dict,
    random_order_shows: list[int],
    config: RandomPlaylistConfig,
    logger: Optional[StructuredLogger] = None
) -> None:
    """
    Build and play a randomized playlist of TV episodes and optionally movies.
    
    Creates a "channel surfing" experience by randomly selecting episodes
    from available TV shows and movies, then playing them as a playlist.
    
    Weighting Algorithm:
        The movieweight setting (0.0-1.0) controls the movie-to-TV-show ratio:
        - movieweight = 0.0: No movies, only TV episodes
        - movieweight = 0.5: Half as many movies as TV shows
        - movieweight = 1.0: Equal number of movies as TV shows with unwatched eps
        
        Formula: movie_limit = min(max(show_count * movieweight, 1), total_movies)
        This ensures at least 1 movie (if available) when movies are enabled.
    
    Candidate Selection:
        1. Filters shows based on population parameter (playlist/user selection)
        2. Retrieves movies based on settings (unwatched/watched/all)
        3. Creates candidate list with prefixed IDs: 't123' for TV, 'm456' for movie
        4. Shuffles combined list for random order
        5. Optionally prioritizes shows with partial progress (start_partials)
    
    Playlist Building:
        - Loops until 'length' items added or all candidates exhausted
        - For TV: adds episode, tracks show in added_ep_dict for multi-episode
        - For movies: adds movie, removes from candidate pool (no duplicates)
        - Skips premiere episodes (S01E01) if 'premieres' setting is false
        - For 'multiple_shows' mode: same show can appear multiple times
    
    Args:
        population: Dict with filter mode:
            - {'playlist': path} - Filter by smart playlist
            - {'usersel': [ids]} - Filter by user selection
            - {'none': ''} - No filtering
        random_order_shows: List of show IDs with random episode ordering
        config: RandomPlaylistConfig with all playlist settings
        logger: Optional logger instance
    
    Side Effects:
        - Clears existing video playlist
        - Sets 'EasyTV.playlist_running' to 'true'
        - Sets 'EasyTV.random_order_shuffle' to 'true'
        - Starts playlist playback via xbmc.Player
    """
    log = logger or _get_log()
    
    # Get filtered show data
    stored_data_filtered = filter_shows_by_population(
        population, config.sort_by, config.sort_reverse, config.language, log
    )
    
    log.info("Building random playlist", event="playlist.create")
    
    # Clear existing playlist
    json_query(get_clear_video_playlist_query(), False)
    
    added_ep_dict: dict = {}
    count = 0
    
    # Determine movie inclusion based on playlist content type
    include_movies = config.playlist_content != CONTENT_TV_ONLY
    movies_enabled = include_movies
    
    # Fetch movies if enabled
    movie_list: list[int] = []
    if include_movies:
        # Convert movie_selection (0=unwatched, 1=watched, 2=both) to booleans
        include_unwatched = config.movie_selection in (0, 2)
        include_watched = config.movie_selection in (1, 2)
        movie_list = _fetch_movies(include_unwatched, include_watched, log)
        movies_enabled = bool(movie_list)
    
    stored_show_count = len(stored_data_filtered)
    moviecount = len(movie_list)
    
    # Handle content-type specific logic
    local_movieweight = config.movieweight
    if config.playlist_content == CONTENT_MOVIES_ONLY:
        # Movies only: clear TV shows, set weight to 0 (no ratio calculation)
        local_movieweight = 0.0
        stored_data_filtered = []
        stored_show_count = 0
    elif config.playlist_content == CONTENT_TV_ONLY:
        # TV only: ensure no movies
        movie_list = []
        moviecount = 0
    
    # Calculate movie limit based on weight (only applies to mixed mode)
    if local_movieweight == 0.0:
        movie_limit_count = 0
    else:
        # movies = shows * weight, but at least 1 and at most available
        movie_limit_count = min(
            max(int(round(stored_show_count * local_movieweight, 0)), 1),
            moviecount
        )
    
    if movies_enabled and movie_limit_count > 0:
        movie_list = movie_list[:movie_limit_count]
        log.debug("Movie list truncated", limit=movie_limit_count)
    
    # Build candidate list with type prefixes
    candidate_list = (
        [f't{x[1]}' for x in stored_data_filtered] +
        [f'm{x}' for x in movie_list]
    )
    random.shuffle(candidate_list)
    
    # Handle start_partials - find most recent partial episode
    partial_start_index: Optional[int] = None
    if config.start_partials:
        partial_start_index = _find_partial_episode_start(candidate_list, log)
    
    # Main playlist building loop
    use_partial_start = partial_start_index is not None
    
    while count < config.length and candidate_list:
        log.debug("Processing candidates", remaining=len(candidate_list))
        
        # Select candidate index
        if use_partial_start and partial_start_index is not None:
            random_index = partial_start_index
            use_partial_start = False
        else:
            random_index = random.randint(0, len(candidate_list) - 1)
        
        log.debug("Selected candidate", index=random_index)
        
        candidate = candidate_list[random_index]
        candidate_type = candidate[0]
        candidate_id = int(candidate[1:])
        
        if candidate_type == 't':
            # TV episode candidate
            log.debug("TV episode candidate", show_id=candidate_id)
            
            episode_id, is_multi = _process_tv_candidate(
                candidate_id, added_ep_dict, candidate_list,
                random_order_shows, config, log
            )
            
            if episode_id is None:
                continue
            
            # Check premiere exclusion
            if _check_premiere_exclusion(candidate_id, candidate_list, config, log):
                continue
            
            # Add episode to playlist
            json_query(build_add_episode_query(episode_id), False)
            log.debug("Episode added to playlist", episode_id=episode_id)
            
            # Update tracking dict
            tmp_details = None
            if is_multi:
                # Get details from find_next_episode result
                _, tmp_details = find_next_episode(
                    candidate_id, random_order_shows,
                    epid=added_ep_dict.get(candidate_id, ['', '', [], ''])[3],
                    eps=added_ep_dict.get(candidate_id, ['', '', [], ''])[2]
                )
            
            _update_added_dict(
                candidate_id, added_ep_dict, random_order_shows,
                is_multi, tmp_details, config
            )
            
        elif candidate_type == 'm':
            # Movie candidate
            log.debug("Movie candidate", movie_id=candidate_id)
            json_query(build_add_movie_query(candidate_id), False)
            candidate_list.remove(f'm{candidate_id}')
            
        else:
            # Unknown type - break out
            count = PLAYLIST_BUILD_BREAK_VALUE
        
        count += 1
    
    # Notify service that playlist is running
    WINDOW.setProperty("EasyTV.playlist_running", 'true')
    WINDOW.setProperty("EasyTV.random_order_shuffle", 'true')
    
    # Start playback
    xbmc.Player().play(xbmc.PlayList(1))
    log.info("Random playlist created and started", event="playlist.start", item_count=count)
