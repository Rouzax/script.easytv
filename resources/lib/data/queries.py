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

Usage:
    from resources.lib.data.queries import get_unwatched_shows_query
    from resources.lib.utils import json_query
    
    result = json_query(get_unwatched_shows_query())
"""
from __future__ import annotations

from typing import Any, Optional

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

def build_show_episodes_query(tvshowid: int) -> dict[str, Any]:
    """
    Get all episodes for a TV show.
    
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
                "season", "episode", "runtime", "resume",
                "playcount", "tvshowid", "lastplayed", "file"
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
    Seek to a position in the current video.
    
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
