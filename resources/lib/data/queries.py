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
JSON-RPC Query Builders for EasyTV.

This module centralizes all Kodi JSON-RPC queries used throughout the addon.
Functions return fresh dictionary copies to avoid mutation issues when queries
are modified before execution.

Naming Convention:
    - get_*_query(): Returns a ready-to-use query dict
    - build_*_query(param): Returns a query dict with parameter substituted

Filter Constants:
    - FILTER_UNWATCHED: Filter for unwatched content (playcount = 0)
    - FILTER_WATCHED: Filter for watched content (playcount > 0)

Usage:
    from resources.lib.data.queries import (
        get_unwatched_shows_query,
        build_random_episodes_query,
        get_episode_filter,
        FILTER_UNWATCHED,
    )
    from resources.lib.utils import json_query
    
    # Simple query
    result = json_query(get_unwatched_shows_query())
    
    # Random episodes with filter
    episode_filter = get_episode_filter(EPISODE_SELECTION_UNWATCHED)
    filters = [episode_filter] if episode_filter else []
    query = build_random_episodes_query(tvshowid=123, filters=filters, limit=10)
    result = json_query(query)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from resources.lib.constants import (
    EPISODE_SELECTION_UNWATCHED,
    EPISODE_SELECTION_WATCHED,
    EPISODE_SELECTION_BOTH,
)


# =============================================================================
# Filter Constants
# =============================================================================
# Reusable filter definitions for playcount-based filtering.
# These are used by episode and movie query builders for consistency.

FILTER_UNWATCHED: Dict[str, str] = {
    'field': 'playcount',
    'operator': 'is',
    'value': '0'
}

FILTER_WATCHED: Dict[str, str] = {
    'field': 'playcount',
    'operator': 'greaterthan',
    'value': '0'
}


def get_episode_filter(selection_mode: int) -> Optional[Dict[str, str]]:
    """
    Get the appropriate playcount filter for the given episode selection mode.
    
    Args:
        selection_mode: One of EPISODE_SELECTION_UNWATCHED (0),
                       EPISODE_SELECTION_WATCHED (1), or EPISODE_SELECTION_BOTH (2).
    
    Returns:
        Filter dict for unwatched/watched, or None for "both" (no filter needed).
    
    Example:
        >>> get_episode_filter(EPISODE_SELECTION_UNWATCHED)
        {'field': 'playcount', 'operator': 'is', 'value': '0'}
        >>> get_episode_filter(EPISODE_SELECTION_BOTH)
        None
    """
    if selection_mode == EPISODE_SELECTION_UNWATCHED:
        return FILTER_UNWATCHED.copy()
    elif selection_mode == EPISODE_SELECTION_WATCHED:
        return FILTER_WATCHED.copy()
    elif selection_mode == EPISODE_SELECTION_BOTH:
        return None
    else:
        # Unknown mode, default to no filter (same as BOTH)
        return None


def get_movie_filter(selection_mode: int) -> Optional[Dict[str, str]]:
    """
    Get the appropriate playcount filter for the given movie selection mode.
    
    This is the movie equivalent of get_episode_filter() for consistency.
    Movie selection uses the same constants as episode selection.
    
    Args:
        selection_mode: One of EPISODE_SELECTION_UNWATCHED (0),
                       EPISODE_SELECTION_WATCHED (1), or EPISODE_SELECTION_BOTH (2).
    
    Returns:
        Filter dict for unwatched/watched, or None for "both" (no filter needed).
    """
    return get_episode_filter(selection_mode)


def build_random_episodes_query(
    tvshowid: int,
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build a query for random episodes from a specific TV show.
    
    Uses server-side randomization and optional limit for efficient
    retrieval of random episode subsets.
    
    Args:
        tvshowid: The Kodi TV show ID.
        filters: Optional list of filter dicts to combine with AND.
                 Use get_episode_filter() to generate watch status filters.
        limit: Optional maximum number of episodes to return.
               When set, uses Kodi's limits parameter for efficiency.
    
    Returns:
        Query dict for VideoLibrary.GetEpisodes with random sort.
    
    Example:
        # Get 10 random unwatched episodes from show 123
        watch_filter = get_episode_filter(EPISODE_SELECTION_UNWATCHED)
        query = build_random_episodes_query(
            tvshowid=123,
            filters=[watch_filter] if watch_filter else [],
            limit=10
        )
    """
    params: Dict[str, Any] = {
        "tvshowid": tvshowid,
        "properties": [
            "season", "episode", "runtime", "resume",
            "playcount", "tvshowid", "lastplayed", "file"
        ],
        "sort": {"method": "random"}
    }
    
    # Add filter if provided
    if filters:
        if len(filters) == 1:
            params["filter"] = filters[0]
        else:
            params["filter"] = {"and": filters}
    
    # Add limit if provided
    if limit is not None and limit > 0:
        params["limits"] = {"end": limit}
    
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodes",
        "params": params
    }


def build_random_movies_query(
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build a query for random movies from the library.
    
    Uses server-side randomization and optional limit for efficient
    retrieval of random movie subsets.
    
    Args:
        filters: Optional list of filter dicts to combine with AND.
                 Use get_movie_filter() to generate watch status filters.
        limit: Optional maximum number of movies to return.
               When set, uses Kodi's limits parameter for efficiency.
    
    Returns:
        Query dict for VideoLibrary.GetMovies with random sort.
    
    Example:
        # Get 5 random watched movies
        watch_filter = get_movie_filter(EPISODE_SELECTION_WATCHED)
        query = build_random_movies_query(
            filters=[watch_filter] if watch_filter else [],
            limit=5
        )
    """
    params: Dict[str, Any] = {
        "properties": ["playcount", "title", "runtime", "resume", "file"],
        "sort": {"method": "random"}
    }
    
    # Add filter if provided
    if filters:
        if len(filters) == 1:
            params["filter"] = filters[0]
        else:
            params["filter"] = {"and": filters}
    
    # Add limit if provided
    if limit is not None and limit > 0:
        params["limits"] = {"end": limit}
    
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetMovies",
        "params": params
    }


def build_inprogress_episodes_query() -> Dict[str, Any]:
    """
    Build a query for all in-progress (partially watched) episodes across all shows.
    
    Uses Kodi's native 'inprogress' filter for optimal performance. This is
    significantly faster than querying each show individually for resume points
    (94ms vs 14,200ms for 142 shows).
    
    Returns:
        Query dict for VideoLibrary.GetEpisodes with inprogress filter.
        Results include all episodes with active resume points.
    
    Example:
        >>> from resources.lib.utils import json_query
        >>> result = json_query(build_inprogress_episodes_query())
        >>> episodes = result.get('episodes', [])
        >>> for ep in episodes:
        ...     print(f"Show {ep['tvshowid']}: S{ep['season']}E{ep['episode']}")
    
    Note:
        The caller is responsible for filtering results by show_ids if only
        certain shows are in scope (e.g., filtered by smart playlist).
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodes",
        "params": {
            "properties": [
                "season", "episode", "playcount", "tvshowid",
                "lastplayed", "resume"
            ],
            "filter": {
                "field": "inprogress",
                "operator": "true",
                "value": ""
            }
        }
    }


def build_inprogress_movies_query() -> Dict[str, Any]:
    """
    Build a query for all in-progress (partially watched) movies.
    
    Uses Kodi's native 'inprogress' filter for optimal performance. This is
    faster than fetching all movies and filtering client-side for resume points
    (109ms vs 427ms).
    
    Returns:
        Query dict for VideoLibrary.GetMovies with inprogress filter.
        Results include all movies with active resume points.
    
    Example:
        >>> from resources.lib.utils import json_query
        >>> result = json_query(build_inprogress_movies_query())
        >>> movies = result.get('movies', [])
        >>> for movie in movies:
        ...     print(f"Movie {movie['movieid']}: resume at {movie['resume']['position']}s")
    
    Note:
        The caller is responsible for filtering results by movie_ids if only
        certain movies are in scope (e.g., filtered by smart playlist).
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetMovies",
        "params": {
            "properties": ["playcount", "lastplayed", "resume"],
            "filter": {
                "field": "inprogress",
                "operator": "true",
                "value": ""
            }
        }
    }


# =============================================================================
# Video Playlist Directory
# =============================================================================

def get_playlist_files_query() -> dict[str, Any]:
    """
    Get list of video playlist files.
    
    Returns:
        Query to retrieve playlist files from special://profile/playlists/video/
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Files.GetDirectory",
        "params": {
            "directory": "special://profile/playlists/video/",
            "media": "video"
        }
    }


# =============================================================================
# Playlist Operations
# =============================================================================

def get_clear_video_playlist_query() -> dict[str, Any]:
    """
    Clear the video playlist (playlistid=1).
    
    Returns:
        Query to clear the video playlist.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Playlist.Clear",
        "params": {
            "playlistid": 1
        }
    }


def build_add_episode_query(episode_id: int) -> dict[str, Any]:
    """
    Add an episode to the video playlist.
    
    Args:
        episode_id: The Kodi episode ID to add.
    
    Returns:
        Query to add the episode to playlist.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Playlist.Add",
        "params": {
            "playlistid": 1,
            "item": {"episodeid": episode_id}
        }
    }


def build_add_movie_query(movie_id: int) -> dict[str, Any]:
    """
    Add a movie to the video playlist.
    
    Args:
        movie_id: The Kodi movie ID to add.
    
    Returns:
        Query to add the movie to playlist.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Playlist.Add",
        "params": {
            "playlistid": 1,
            "item": {"movieid": movie_id}
        }
    }


# =============================================================================
# Movie Queries
# =============================================================================

def get_unwatched_movies_query() -> dict[str, Any]:
    """
    Get all unwatched movies (playcount = 0).
    
    Returns:
        Query for unwatched movies with playcount and title properties.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetMovies",
        "params": {
            "filter": {
                "field": "playcount",
                "operator": "is",
                "value": "0"
            },
            "properties": ["playcount", "title"]
        }
    }


def get_watched_movies_query() -> dict[str, Any]:
    """
    Get all watched movies (playcount >= 1).
    
    Returns:
        Query for watched movies with playcount and title properties.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetMovies",
        "params": {
            "filter": {
                "field": "playcount",
                "operator": "greaterthan",
                "value": "0"
            },
            "properties": ["playcount", "title"]
        }
    }


def get_all_movies_query() -> dict[str, Any]:
    """
    Get all movies regardless of watch status.
    
    Returns:
        Query for all movies with playcount and title properties.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetMovies",
        "params": {
            "properties": ["playcount", "title"]
        }
    }


# =============================================================================
# TV Show Queries
# =============================================================================

def get_unwatched_shows_query() -> dict[str, Any]:
    """
    Get TV shows with unwatched episodes.
    
    Returns:
        Query for shows with unwatched episodes, including metadata
        for display (genre, title, mpaa, episode counts, thumbnail).
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetTVShows",
        "params": {
            "filter": {
                "field": "playcount",
                "operator": "is",
                "value": "0"
            },
            "properties": [
                "genre", "title", "playcount", "mpaa",
                "watchedepisodes", "episode", "thumbnail"
            ]
        }
    }


def get_all_shows_query() -> dict[str, Any]:
    """
    Get all TV shows (for title lookup).
    
    Returns:
        Query for all shows with title property only.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetTVShows",
        "params": {
            "properties": ["title"]
        }
    }


def get_shows_by_lastplayed_query() -> dict[str, Any]:
    """
    Get TV shows with unwatched episodes, sorted by last played.
    
    Returns:
        Query for shows sorted by lastplayed descending (most recent first).
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetTVShows",
        "params": {
            "filter": {
                "field": "playcount",
                "operator": "is",
                "value": "0"
            },
            "properties": ["lastplayed"],
            "sort": {
                "order": "descending",
                "method": "lastplayed"
            }
        }
    }


def build_show_details_query(tvshowid: int) -> dict[str, Any]:
    """
    Get details for a specific TV show.
    
    Args:
        tvshowid: The Kodi TV show ID.
    
    Returns:
        Query for show details including title.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetTVShowDetails",
        "params": {
            "tvshowid": tvshowid,
            "properties": ["title"]
        }
    }


# =============================================================================
# Episode Queries
# =============================================================================

def build_all_episodes_query() -> dict[str, Any]:
    """
    Get all episodes from all TV shows with full details.
    
    Used for bulk refresh at startup/rescan to minimize JSON-RPC calls.
    Returns episodes for ALL shows; caller filters to relevant show IDs.
    
    Properties included:
        - For next-episode calculation: season, episode, playcount, tvshowid, file
        - For display caching: title, showtitle, plot, firstaired, resume, art
    
    Returns:
        Query for all episodes with calculation and display fields.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodes",
        "params": {
            "properties": [
                # For next-episode calculation
                "season", "episode", "playcount", "tvshowid", "file",
                # For display caching
                "title", "showtitle", "plot", "firstaired", "resume", "art"
            ]
        }
    }


def build_show_episodes_query(tvshowid: int) -> dict[str, Any]:
    """
    Get all episodes for a TV show.
    
    Used for non-bulk episode queries (single show refresh after playback).
    
    Args:
        tvshowid: The Kodi TV show ID.
    
    Returns:
        Query for all episodes with playback-relevant properties.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodes",
        "params": {
            "tvshowid": tvshowid,
            "properties": [
                "season", "episode", "playcount", "tvshowid", "file"
            ]
        }
    }


def build_episode_details_query(episode_id: int) -> dict[str, Any]:
    """
    Get full details for a specific episode.
    
    Args:
        episode_id: The Kodi episode ID.
    
    Returns:
        Query for comprehensive episode details (for display/playback).
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodeDetails",
        "params": {
            "episodeid": episode_id,
            "properties": [
                "title", "playcount", "plot", "season", "episode",
                "showtitle", "file", "lastplayed", "rating", "resume",
                "art", "streamdetails", "firstaired", "runtime", "tvshowid"
            ]
        }
    }


def build_episode_playcount_query(episode_id: int) -> dict[str, Any]:
    """
    Get playcount and show ID for an episode.
    
    Args:
        episode_id: The Kodi episode ID.
    
    Returns:
        Query for episode playcount and tvshowid.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodeDetails",
        "params": {
            "episodeid": episode_id,
            "properties": ["playcount", "tvshowid"]
        }
    }


def build_episode_show_id_query(episode_id: int) -> dict[str, Any]:
    """
    Get the TV show ID and last played date for an episode.
    
    Used for iStream fix and episode-to-show mapping.
    
    Args:
        episode_id: The Kodi episode ID.
    
    Returns:
        Query for episode's tvshowid and lastplayed.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodeDetails",
        "params": {
            "episodeid": episode_id,
            "properties": ["lastplayed", "tvshowid"]
        }
    }


def build_episode_prompt_info_query(episode_id: int) -> dict[str, Any]:
    """
    Get episode info for the "next episode" prompt dialog.
    
    Args:
        episode_id: The Kodi episode ID.
    
    Returns:
        Query for season, episode number, show title, and show ID.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.GetEpisodeDetails",
        "params": {
            "episodeid": episode_id,
            "properties": ["season", "episode", "showtitle", "tvshowid"]
        }
    }


# =============================================================================
# Player Queries
# =============================================================================

def get_playing_item_query() -> dict[str, Any]:
    """
    Get information about the currently playing video.
    
    Returns:
        Query for current player item with show/episode info.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Player.GetItem",
        "params": {
            "playerid": 1,
            "properties": [
                "showtitle", "tvshowid", "episode",
                "season", "playcount", "resume"
            ]
        }
    }


def build_player_seek_query(position: float) -> dict[str, Any]:
    """
    Seek to a position in the current video by percentage.
    
    Args:
        position: Percentage position (0.0 - 100.0).
    
    Returns:
        Query to seek to the specified percentage.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Player.Seek",
        "params": {
            "playerid": 1,
            "value": {"percentage": position}
        }
    }


def build_player_seek_time_query(seconds: int) -> dict[str, Any]:
    """
    Seek to an absolute time position in the current video.
    
    Args:
        seconds: Time in seconds from start of video.
    
    Returns:
        Query to seek to the specified time.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Player.Seek",
        "params": {
            "playerid": 1,
            "value": {
                "time": {
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": secs,
                    "milliseconds": 0
                }
            }
        }
    }


# =============================================================================
# Batch Operations
# =============================================================================

def build_set_episode_details_query(
    episode_id: int,
    playcount: Optional[int] = None,
    lastplayed: Optional[str] = None,
    resume: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Build a query to update episode details (playcount, lastplayed, resume).
    
    Args:
        episode_id: The Kodi episode ID.
        playcount: New playcount value (optional).
        lastplayed: New lastplayed date string (optional).
        resume: Resume position dict with 'position' and 'total' (optional).
    
    Returns:
        Query to update the episode details.
    """
    params: dict[str, Any] = {"episodeid": episode_id}
    
    if playcount is not None:
        params["playcount"] = playcount
    if lastplayed is not None:
        params["lastplayed"] = lastplayed
    if resume is not None:
        params["resume"] = resume
    
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "VideoLibrary.SetEpisodeDetails",
        "params": params
    }


def build_playlist_get_items_query(playlist_path: str) -> dict[str, Any]:
    """
    Get contents of a smart playlist file.
    
    Args:
        playlist_path: Path to the .xsp playlist file.
    
    Returns:
        Query to retrieve playlist contents.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Files.GetDirectory",
        "params": {
            "directory": playlist_path,
            "media": "video",
            "properties": ["tvshowid"]
        }
    }


# =============================================================================
# Addon Control
# =============================================================================

def build_addon_enabled_query(addon_id: str, enabled: bool) -> dict[str, Any]:
    """
    Enable or disable an addon.
    
    Args:
        addon_id: The addon ID (e.g., 'script.easytv').
        enabled: True to enable, False to disable.
    
    Returns:
        Query to set addon enabled state.
    """
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Addons.SetAddonEnabled",
        "params": {
            "addonid": addon_id,
            "enabled": enabled
        }
    }
