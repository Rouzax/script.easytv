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
TV Show Data Functions for EasyTV.

This module provides functions for fetching, filtering, sorting, and processing
TV show and episode data from the Kodi library.

Functions are designed to be pure where possible, taking necessary context
as parameters rather than relying on global state.

Logging:
    Logger: 'data' (via get_logger)
    Key events:
        - library.fetch (DEBUG): TV shows fetched from library
        - library.fallback (WARNING): No shows found in library
        - data.sort (DEBUG): Show sorting operations
        - data.istream (DEBUG): iStream episode resolution
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import ast
import os
import random
from typing import Any, Callable, Optional, Union

import xbmc
import xbmcgui

from resources.lib.utils import json_query, get_logger, parse_lastplayed_date, lang, log_timing
from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    SEASON_START_EPISODE,
    CATEGORY_START_FRESH,
    CATEGORY_CONTINUE_WATCHING,
    ISTREAM_FIX_MAX_RETRIES,
)
from resources.lib.data.queries import (
    get_all_shows_query,
    build_show_episodes_query,
    build_show_details_query,
    build_episode_details_query,
    build_playlist_get_items_query,
)


# Module-level logger
log = get_logger('data')

# Window reference for property access
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)


# =============================================================================
# Article Stripping Configuration by Language
# =============================================================================
# Maps languages to their leading articles that should be stripped for sorting
LANGUAGE_ARTICLES: dict[str, list[str]] = {
    'English': ['the '],
    'Russian': ['the '],
    'Polish': ['the '],
    'Turkish': ['the '],
    'Spanish': ['la ', 'los ', 'las ', 'el ', 'lo '],
    'Dutch': ['de ', 'het '],
    'Danish': ['de ', 'det ', 'den '],
    'Swedish': ['de ', 'det ', 'den '],
    'German': ['die ', 'der ', 'den ', 'das '],
    'Afrikaans': ['die ', 'der ', 'den ', 'das '],
    'French': ['les ', 'la ', 'le '],
}


# =============================================================================
# Sorting and Name Processing
# =============================================================================

def generate_sort_key(raw_name: str, language: str = 'English') -> str:
    """
    Generate a sort key by stripping leading articles based on language.
    
    For proper alphabetical sorting of show titles, removes common leading
    articles (like "The", "Die", "Los") based on the user's language setting.
    
    Args:
        raw_name: The original show title.
        language: The user's language (from Kodi's System.Language).
    
    Returns:
        Lowercase name with leading article removed if applicable.
    
    Examples:
        generate_sort_key("The Office", "English") -> "office"
        generate_sort_key("Die Simpsons", "German") -> "simpsons"
        generate_sort_key("Breaking Bad", "English") -> "breaking bad"
    """
    name = raw_name.lower()
    
    # Check for language-specific articles
    articles = None
    
    # Handle compound language names like "English (US)"
    for lang_key, lang_articles in LANGUAGE_ARTICLES.items():
        if lang_key in language:
            articles = lang_articles
            break
    
    if articles:
        for article in articles:
            if name.startswith(article):
                return name[len(article):]
    
    return name


# =============================================================================
# Episode Data Functions
# =============================================================================

def parse_season_episode_string(value: Union[int, str]) -> str:
    """
    Pad season/episode numbers to two digits for consistent formatting.
    
    This ensures consistent string comparison for episode matching,
    particularly needed for iStream content.
    
    Args:
        value: Season or episode number (string or int).
    
    Returns:
        Two-digit string (e.g., "01", "12").
    
    Examples:
        parse_season_episode_string(1) -> "01"
        parse_season_episode_string("5") -> "05"
        parse_season_episode_string(12) -> "12"
    """
    str_value = str(value)
    if len(str_value) == 1:
        return '0' + str_value
    return str_value


def find_next_episode(
    showid: int,
    random_order_shows: list[int],
    epid: Optional[int] = None,
    eps: Optional[list[int]] = None
) -> tuple[Optional[int], Optional[list]]:
    """
    Determine the next episode to play for a given show.
    
    For shows in random order mode, shuffles available episodes and picks one.
    For sequential shows, returns the next episode in the list.
    
    Args:
        showid: The TV show ID.
        random_order_shows: List of show IDs configured for random playback.
        epid: Current episode ID (to exclude from selection).
        eps: List of available episode IDs.
    
    Returns:
        Tuple of (next_episode_id, [season, episode, remaining_eps, ep_id])
        Returns (None, None) if no next episode.
    """
    if eps is None:
        eps = []
    
    log.debug("Finding next episode", show_id=showid, random_mode=showid in random_order_shows)
    
    if not eps:
        return None, None
    
    if showid in random_order_shows:
        # Random order: shuffle and pick, excluding current episode
        available = eps[:]
        if epid is not None and epid in available:
            available.remove(epid)
        
        if not available:
            return None, None
        
        random.shuffle(available)
        next_ep = available[0]
        remaining = available
    else:
        # Sequential order: get next in list
        try:
            next_ep = eps[1]
            remaining = eps[1:]
        except IndexError:
            return None, None
    
    # Get details of next episode
    ep_details = json_query(build_episode_details_query(next_ep), True)
    
    if 'episodedetails' in ep_details and ep_details['episodedetails']:
        details = ep_details['episodedetails']
        return next_ep, [details['season'], details['episode'], remaining, next_ep]
    
    return None, None


# =============================================================================
# Show Fetching and Sorting
# =============================================================================

def merge_and_sort_shows(
    shows_from_query: list[dict[str, Any]],
    shows_from_service: list[int],
    sort_by: int,
    sort_reverse: bool,
    language: str = 'English'
) -> list[list]:
    """
    Merge query results with service data and sort according to user preference.
    
    Args:
        shows_from_query: Raw show data from Kodi's JSON-RPC query.
        shows_from_service: List of show IDs that have next episodes cached.
        sort_by: Sort method (0=name, 1=lastplayed, 2=unwatched, 3=watched, 4=season).
        sort_reverse: If True, reverse the sort order.
        language: User's language for article stripping.
    
    Returns:
        Sorted list of [lastplayed_timestamp, showid] pairs.
    """
    log.debug("Sorting shows", method=sort_by, reverse=sort_reverse)
    
    if sort_by == 0:
        # SORT BY show name
        intermediate = [
            [x['label'], 
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
             x['tvshowid']] 
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        intermediate.sort(key=lambda x: generate_sort_key(x[0], language), reverse=sort_reverse)
        return [x[1:] for x in intermediate]
    
    elif sort_by == 2:
        # Sort by Unwatched Episodes count
        intermediate = [
            [int(WINDOW.getProperty("EasyTV.%s.CountonDeckEps" % x['tvshowid']) or 0),
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0,
             x['tvshowid']]
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        # Default is descending; sort_reverse inverts to ascending
        intermediate.sort(reverse=not sort_reverse)
        return [x[1:] for x in intermediate]
    
    elif sort_by == 3:
        # Sort by Watched Episodes count
        intermediate = [
            [int(WINDOW.getProperty("EasyTV.%s.CountWatchedEps" % x['tvshowid']) or 0),
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0,
             x['tvshowid']]
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        intermediate.sort(reverse=not sort_reverse)
        return [x[1:] for x in intermediate]
    
    elif sort_by == 4:
        # Sort by Season number
        intermediate = [
            [int(WINDOW.getProperty("EasyTV.%s.Season" % x['tvshowid']) or 0),
             parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0,
             x['tvshowid']]
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        intermediate.sort(reverse=not sort_reverse)
        return [x[1:] for x in intermediate]
    
    else:
        # Default: SORT BY LAST WATCHED (sort_by == 1 or other)
        intermediate = [
            [parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
             x['tvshowid']] 
            for x in shows_from_query if x['tvshowid'] in shows_from_service
        ]
        
        # Separate never-watched shows (timestamp == 0)
        never_watched = [x for x in intermediate if x[0] == 0]
        watched = [x for x in intermediate if x[0] != 0]
        
        # Default is descending; sort_reverse inverts to ascending
        watched.sort(reverse=not sort_reverse)
        
        return watched + never_watched


def fetch_unwatched_shows(sort_by: int, sort_reverse: bool, language: str = 'English') -> list[list]:
    """
    Fetch all TV shows with unwatched episodes, sorted by user preference.
    
    Retrieves shows from Kodi's library and cross-references with the service's
    cached show data. Returns only shows that have next episodes ready.
    
    Args:
        sort_by: Sort method (0=name, 1=lastplayed, 2=unwatched, 3=watched, 4=season).
        sort_reverse: If True, reverse the sort order.
        language: User's language for article stripping.
    
    Returns:
        List of [lastplayed_timestamp, showid, episode_id] triples.
    
    Raises:
        SystemExit: If no shows available from service.
    """
    import sys
    import json
    
    with log_timing(log, "fetch_unwatched_shows", sort_by=sort_by) as timer:
        log.debug("Fetching TV shows", sort_by=sort_by)
        
        # Query Kodi for shows with unwatched episodes
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "filter": {"field": "playcount", "operator": "is", "value": "0"},
                "properties": ["lastplayed"],
                "sort": {"order": "descending", "method": "lastplayed"}
            },
            "id": "1"
        }
        
        response = xbmc.executeJSONRPC(json.dumps(query))
        data = json.loads(response)
        
        if 'result' in data and 'tvshows' in data['result'] and data['result']['tvshows']:
            shows_from_query = data['result']['tvshows']
            log.debug("TV shows found", count=len(shows_from_query))
        else:
            log.warning("No unwatched TV shows in library", event="library.fallback")
            shows_from_query = []
        
        timer.mark("query")
        
        # Get shows with cached next episodes from service
        shows_str = WINDOW.getProperty("EasyTV.shows_with_next_episodes")
        
        if shows_str:
            shows_from_service = [int(x) for x in ast.literal_eval(shows_str)]
        else:
            # Service not ready - this is handled by the caller
            from resources.lib.utils import lang
            dialog = xbmcgui.Dialog()
            dialog.ok('EasyTV', lang(32115) + '\n' + lang(32116))
            sys.exit()
        
        sorted_shows = merge_and_sort_shows(
            shows_from_query, shows_from_service, sort_by, sort_reverse, language
        )
        
        timer.mark("sort")
        
        # Add episode IDs from service cache
        stored_data = [
            [x[0], x[1], WINDOW.getProperty("EasyTV.%s.EpisodeID" % x[1])] 
            for x in sorted_shows
        ]
        
        timer.mark("property_lookup")
        
        log.debug("TV shows fetch complete", count=len(stored_data))
    
    return stored_data


def fetch_shows_with_watched_episodes(
    sort_by: int, 
    sort_reverse: bool, 
    language: str = 'English'
) -> list[list]:
    """
    Fetch all TV shows that have at least one watched episode.
    
    Unlike fetch_unwatched_shows, this queries Kodi directly without relying
    on the service cache. Used for "watched" and "both" episode selection modes.
    
    Args:
        sort_by: Sort method (0=name, 1=lastplayed).
        sort_reverse: If True, reverse the sort order.
        language: User's language for article stripping.
    
    Returns:
        List of [lastplayed_timestamp, showid, ''] triples. The episode_id
        field is empty because watched episodes are selected on-demand.
    """
    import json
    
    with log_timing(log, "fetch_shows_with_watched_episodes", sort_by=sort_by) as timer:
        log.debug("Fetching shows with watched episodes", sort_by=sort_by)
        
        # Query Kodi for shows with watched episodes (playcount > 0)
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "filter": {"field": "playcount", "operator": "greaterthan", "value": "0"},
                "properties": ["lastplayed"],
                "sort": {"order": "descending", "method": "lastplayed"}
            },
            "id": "1"
        }
        
        response = xbmc.executeJSONRPC(json.dumps(query))
        data = json.loads(response)
        
        if 'result' in data and 'tvshows' in data['result'] and data['result']['tvshows']:
            shows_from_query = data['result']['tvshows']
            log.debug("Shows with watched episodes found", count=len(shows_from_query))
        else:
            log.debug("No shows with watched episodes found")
            return []
        
        timer.mark("query")
        
        # Sort the shows
        if sort_by == 0:
            # Sort by show name
            intermediate = [
                [x['label'], 
                 parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
                 x['tvshowid']] 
                for x in shows_from_query
            ]
            intermediate.sort(key=lambda x: generate_sort_key(x[0], language), reverse=sort_reverse)
            sorted_shows = [[x[1], x[2]] for x in intermediate]
        else:
            # Default: sort by last played
            intermediate = [
                [parse_lastplayed_date(x['lastplayed']) if x.get('lastplayed') else 0, 
                 x['tvshowid']] 
                for x in shows_from_query
            ]
            
            # Separate never-watched shows (timestamp == 0)
            never_watched = [x for x in intermediate if x[0] == 0]
            watched = [x for x in intermediate if x[0] != 0]
            watched.sort(reverse=not sort_reverse)
            sorted_shows = watched + never_watched
        
        timer.mark("sort")
        
        # Return with empty episode_id field (episodes selected on-demand)
        stored_data = [[x[0], x[1], ''] for x in sorted_shows]
        
        log.debug("Shows with watched episodes fetch complete", count=len(stored_data))
    
    return stored_data


def extract_showids_from_playlist(playlist_path: str) -> list[int]:
    """
    Extract TV show IDs from a smart playlist file.
    
    Reads the contents of a video smart playlist and returns the IDs
    of all TV shows contained within it. Shows an error dialog if the
    playlist is empty or contains no TV shows.
    
    Args:
        playlist_path: Full path to the playlist file.
    
    Returns:
        List of TV show IDs in the playlist, or empty list on error.
    """
    # Normalize path to Kodi's special:// format
    filename = os.path.split(playlist_path)[1]
    clean_path = 'special://profile/playlists/video/' + filename
    
    playlist_contents = json_query(build_playlist_get_items_query(clean_path), True)
    
    dialog = xbmcgui.Dialog()
    
    if 'files' not in playlist_contents:
        dialog.ok("EasyTV", lang(32575))
        return []
    
    if not playlist_contents['files']:
        dialog.ok("EasyTV", lang(32576))
        return []
    
    filtered_showids = [
        x['id'] for x in playlist_contents['files'] 
        if x.get('type') == 'tvshow'
    ]
    
    log.debug("Shows extracted from playlist", show_ids=filtered_showids)
    
    if not filtered_showids:
        dialog.ok("EasyTV", lang(32577))
        return []
    
    return filtered_showids


def extract_movieids_from_playlist(playlist_path: str) -> list[int]:
    """
    Extract movie IDs from a smart playlist file.
    
    Reads the contents of a video smart playlist and returns the IDs
    of all movies contained within it. Shows an error dialog if the
    playlist is empty or contains no movies.
    
    Args:
        playlist_path: Full path to the playlist file.
    
    Returns:
        List of movie IDs in the playlist, or empty list on error.
    """
    # Normalize path to Kodi's special:// format
    filename = os.path.split(playlist_path)[1]
    clean_path = 'special://profile/playlists/video/' + filename
    
    playlist_contents = json_query(build_playlist_get_items_query(clean_path), True)
    
    dialog = xbmcgui.Dialog()
    
    if 'files' not in playlist_contents:
        dialog.ok("EasyTV", lang(32575))
        return []
    
    if not playlist_contents['files']:
        dialog.ok("EasyTV", lang(32576))
        return []
    
    filtered_movieids = [
        x['id'] for x in playlist_contents['files'] 
        if x.get('type') == 'movie'
    ]
    
    log.debug("Movies extracted from playlist", movie_ids=filtered_movieids)
    
    if not filtered_movieids:
        # 32605 = "Error: no movies in playlist"
        dialog.ok("EasyTV", lang(32605))
        return []
    
    return filtered_movieids


# =============================================================================
# Smart Playlist Categorization
# =============================================================================

def get_show_category(episode_number: int) -> str:
    """
    Determine which category playlist a show belongs to based on episode number.
    
    Episode 1 of any season means the user hasn't started watching that season yet,
    so it goes in "Start Fresh". Episode 2+ means they're mid-season, so it goes
    in "Continue Watching".
    
    Args:
        episode_number: The episode number (1, 2, 3, etc.)
    
    Returns:
        CATEGORY_START_FRESH if episode == 1, CATEGORY_CONTINUE_WATCHING otherwise.
    """
    if episode_number == SEASON_START_EPISODE:
        return CATEGORY_START_FRESH
    return CATEGORY_CONTINUE_WATCHING


def fetch_show_episode_data(tvshowid: int) -> Optional[dict[str, Any]]:
    """
    Retrieve show data from Window properties for smart playlist operations.
    
    Fetches cached show information from the service's window properties,
    with a fallback to Kodi's library if the title isn't cached.
    
    Args:
        tvshowid: The TV show ID.
    
    Returns:
        Dict with keys: showname, filename, episode_number, episodeno
        Returns None if essential data (showname) is not available.
    """
    showname = WINDOW.getProperty("EasyTV.%s.TVshowTitle" % tvshowid)
    filename = os.path.basename(WINDOW.getProperty("EasyTV.%s.File" % tvshowid))
    episodeno = WINDOW.getProperty("EasyTV.%s.EpisodeNo" % tvshowid)
    episode_str = WINDOW.getProperty("EasyTV.%s.Episode" % tvshowid)
    
    # Fallback: lookup show name from Kodi library if Window property not set
    if not showname:
        result = json_query(build_show_details_query(tvshowid), True)
        showname = result.get('tvshowdetails', {}).get('title', '')
    
    if not showname:
        return None
    
    # Parse episode number, default to 1 if parsing fails
    try:
        episode_number = int(episode_str) if episode_str else SEASON_START_EPISODE
    except (ValueError, TypeError):
        episode_number = SEASON_START_EPISODE
    
    return {
        'showname': showname,
        'filename': filename,
        'episode_number': episode_number,
        'episodeno': episodeno
    }


# =============================================================================
# iStream Compatibility
# =============================================================================

def resolve_istream_episode(
    now_playing_show_id: int,
    showtitle: str,
    episode_np: str,
    season_np: str,
    random_order_shows: list[int],
    refresh_callback: Optional[Callable[[list[int]], None]] = None
) -> tuple[bool, int, Union[int, bool]]:
    """
    Handle streams from iStream that don't provide showid and epid.
    
    iStream streams come through as tvshowid=-1 but include episode/season/show name.
    This function looks up the correct IDs from the Kodi library.
    
    Args:
        now_playing_show_id: TV show ID (-1 for iStream).
        showtitle: Name of the TV show.
        episode_np: Episode number (formatted).
        season_np: Season number (formatted).
        random_order_shows: List of show IDs in random playback mode.
        refresh_callback: Optional callback to refresh episode data for a show.
                         Called with [show_id] when episode not in ondeck list.
    
    Returns:
        Tuple of (previous_episode_check_flag, show_id, episode_id)
        previous_episode_check_flag is always False for iStream content.
    """
    now_playing_episode_id: Union[int, bool] = False
    
    log.debug("Resolving iStream episode", 
              show_id=now_playing_show_id, title=showtitle, 
              episode=episode_np, season=season_np)
    
    redo = True
    count = 0
    
    while redo and count < ISTREAM_FIX_MAX_RETRIES:
        redo = False
        count += 1
        
        if now_playing_show_id == -1 and showtitle and episode_np and season_np:
            # Look up show by title
            tmp_shows = json_query(get_all_shows_query(), True)
            log.debug("TV shows query for iStream", shows=tmp_shows)
            
            if 'tvshows' in tmp_shows:
                for show in tmp_shows['tvshows']:
                    if show['label'] == showtitle:
                        now_playing_show_id = show['tvshowid']
                        
                        # Look up episode by season/episode number
                        tmp_eps = json_query(build_show_episodes_query(now_playing_show_id), True)
                        log.debug("Episodes query for iStream", episodes=tmp_eps)
                        
                        if 'episodes' in tmp_eps:
                            for ep in tmp_eps['episodes']:
                                if (parse_season_episode_string(ep['season']) == season_np and 
                                    parse_season_episode_string(ep['episode']) == episode_np):
                                    now_playing_episode_id = ep['episodeid']
                                    log.debug("Found episode in library", episode_id=now_playing_episode_id)
                                    
                                    # Check if episode is in ondeck list
                                    ondeck_str = WINDOW.getProperty(
                                        "EasyTV.%s.ondeck_list" % now_playing_show_id
                                    )
                                    
                                    if ondeck_str:
                                        temp_ondeck_list = ast.literal_eval(ondeck_str)
                                    else:
                                        temp_ondeck_list = []
                                    
                                    # Include offdeck episodes for random order shows
                                    if now_playing_show_id in random_order_shows:
                                        offdeck_str = WINDOW.getProperty(
                                            "EasyTV.%s.offdeck_list" % now_playing_show_id
                                        )
                                        if offdeck_str:
                                            temp_ondeck_list += ast.literal_eval(offdeck_str)
                                    
                                    log.debug("On-deck list for iStream", 
                                             ondeck=temp_ondeck_list, 
                                             episode_id=now_playing_episode_id)
                                    
                                    if now_playing_episode_id not in temp_ondeck_list:
                                        log.debug("iStream fix: episode not in ondeck, refreshing")
                                        if refresh_callback:
                                            refresh_callback([now_playing_show_id])
                                        log.debug("iStream fix: refresh complete")
                                        redo = True
                                    
                                    break
                        break
    
    return False, now_playing_show_id, now_playing_episode_id
