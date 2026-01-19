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
EasyTV Settings Management.

Handles loading, persisting, and initializing addon settings for the service.
Extracted from service.py as part of modularization.

Logging:
    Module: settings
    Events:
        - settings.load (INFO): Settings loaded with full configuration
        - settings.reload (INFO): Settings reloaded during runtime
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TYPE_CHECKING

import xbmcaddon
import xbmcgui

from resources.lib.constants import KODI_HOME_WINDOW_ID
from resources.lib.utils import (
    get_addon,
    json_query,
    lang,
    get_logger,
)
from resources.lib.data.queries import build_show_details_query

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('settings')
    return _log


# Type alias for callback functions used by load_settings
# Note: Use List instead of list for Python 3.8 compatibility (Kodi uses 3.8)
RandomOrderCallback = Callable[[int], None]
StoreNextEpCallback = Callable[[int, int, List, List, int, int], None]
RemoveShowCallback = Callable[[int], None]
UpdatePlaylistCallback = Callable[[int], None]


@dataclass
class ServiceSettings:
    """
    Container for all service settings.
    
    Groups all settings loaded from the addon configuration into a single
    object for easier passing between components.
    """
    # Notification and display
    playlist_notifications: bool = True
    
    # Playback behavior - separate TV and movie resume settings
    resume_partials_tv: bool = True
    resume_partials_movies: bool = True
    nextprompt: bool = False
    nextprompt_in_playlist: bool = False
    previous_episode_check: bool = False
    
    # Prompt configuration
    promptduration: int = 0
    promptdefaultaction: int = 0
    
    # Playlist continuation
    playlist_continuation: bool = False
    playlist_continuation_duration: int = 20
    
    # Feature flags
    startup: bool = False
    maintainsmartplaylist: bool = False
    
    # Random order shows (list of show IDs)
    random_order_shows: list[int] = field(default_factory=list)
    
    # Logging
    keep_logs: bool = False


def init_display_settings(addon: Optional[xbmcaddon.Addon] = None) -> None:
    """
    Initialize display settings with current stored values.
    
    Called on first run and on settings reload to ensure display settings 
    show correct values when the settings dialog is opened.
    
    Args:
        addon: The addon instance. If None, uses get_addon().
    """
    log = _get_log()
    
    if addon is None:
        addon = get_addon()
    
    setting = addon.getSetting
    
    # Random order shows display
    try:
        random_shows = ast.literal_eval(setting('random_order_shows'))
        count = len(random_shows) if random_shows and random_shows != 'none' else 0
    except (ValueError, SyntaxError):
        count = 0
    display_text = lang(32569) % count if count > 0 else lang(32571)
    addon.setSetting(id="random_order_shows_display", value=display_text)
    log.debug("Init random_order_shows_display", value=display_text, count=count)
    
    # Selection (usersel) display
    try:
        selection = ast.literal_eval(setting('selection'))
        count = len(selection) if selection and selection != 'none' else 0
    except (ValueError, SyntaxError):
        count = 0
    display_text = lang(32569) % count if count > 0 else lang(32571)
    addon.setSetting(id="selection_display", value=display_text)
    log.debug("Init selection_display", value=display_text, count=count)
    
    # Playlist file display
    playlist_path = setting('user_playlist_path')
    if playlist_path and playlist_path != 'none' and playlist_path != 'empty':
        filename = os.path.basename(playlist_path)
        if filename.endswith('.xsp'):
            filename = filename[:-4]
        display_text = filename
    else:
        display_text = lang(32570)
    addon.setSetting(id="playlist_file_display", value=display_text)
    log.debug("Init playlist_file_display", value=display_text, path=playlist_path)
    
    # Movie playlist file display
    movie_playlist_path = setting('movie_user_playlist_path')
    if movie_playlist_path and movie_playlist_path != 'none' and movie_playlist_path != 'empty':
        filename = os.path.basename(movie_playlist_path)
        if filename.endswith('.xsp'):
            filename = filename[:-4]
        display_text = filename
    else:
        display_text = lang(32603)  # "All movies"
    addon.setSetting(id="movie_playlist_file_display", value=display_text)
    log.debug("Init movie_playlist_file_display", value=display_text, path=movie_playlist_path)


def load_settings(
    firstrun: bool = False,
    window: Optional[xbmcgui.Window] = None,
    addon: Optional[xbmcaddon.Addon] = None,
    logger: Optional[StructuredLogger] = None,
    # Callbacks for Main class interactions
    on_add_random_show: Optional[RandomOrderCallback] = None,
    on_reshuffle_random_shows: Optional[Callable[[list[int]], None]] = None,
    on_store_next_ep: Optional[StoreNextEpCallback] = None,
    on_remove_show: Optional[RemoveShowCallback] = None,
    on_update_smartplaylist: Optional[UpdatePlaylistCallback] = None,
    shows_with_next_episodes: Optional[list[int]] = None,
) -> ServiceSettings:
    """
    Load all settings from the addon configuration.
    
    On first run, also initializes display settings. On subsequent calls,
    handles changes to random_order_shows by calling the appropriate callbacks.
    
    Args:
        firstrun: True if this is the initial load at service startup.
        window: The Kodi home window instance. If None, creates one.
        addon: The addon instance. If None, uses get_addon().
        logger: Logger instance to use. If None, uses module logger.
        on_add_random_show: Callback when a show is added to random order.
        on_reshuffle_random_shows: Callback to reshuffle random shows.
        on_store_next_ep: Callback to store next episode for a show.
        on_remove_show: Callback to remove a show from tracking.
        on_update_smartplaylist: Callback to update smart playlists.
        shows_with_next_episodes: Current list of tracked shows.
    
    Returns:
        ServiceSettings containing all loaded settings.
    """
    log = logger or _get_log()
    
    if window is None:
        window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    
    # For settings reload (not firstrun), get a fresh addon instance
    # to ensure we read the updated values from Kodi
    if addon is None or not firstrun:
        addon = xbmcaddon.Addon()
    
    setting = addon.getSetting
    
    # Load all settings
    settings = ServiceSettings(
        playlist_notifications=setting("notify") == 'true',
        resume_partials_tv=setting('resume_partials_tv') == 'true',
        resume_partials_movies=setting('resume_partials_movies') == 'true',
        keep_logs=setting('logging') == 'true',
        nextprompt=setting('nextprompt') == 'true',
        nextprompt_in_playlist=setting('nextprompt_in_playlist') == 'true',
        startup=setting('startup') == 'true',
        promptduration=int(float(setting('promptduration'))),
        previous_episode_check=setting('previous_episode_check') == 'true',
        promptdefaultaction=int(float(setting('promptdefaultaction'))),
        playlist_continuation=setting('playlist_continuation') == 'true',
        playlist_continuation_duration=int(float(setting('playlist_continuation_duration'))),
    )
    
    # Handle maintainsmartplaylist setting
    # Note: We only parse the setting here. The actual playlist updates
    # are triggered in daemon._on_settings_changed() AFTER self._settings
    # is updated, to avoid race condition where _update_smartplaylist
    # checks self._settings.maintainsmartplaylist (the old value).
    settings.maintainsmartplaylist = setting('maintainsmartplaylist') == 'true'
    
    # Parse random_order_shows
    try:
        settings.random_order_shows = ast.literal_eval(setting('random_order_shows'))
    except (ValueError, SyntaxError):
        settings.random_order_shows = []
    
    # Get previous random_order_shows from window property
    try:
        old_random_order_shows = ast.literal_eval(
            window.getProperty("EasyTV.random_order_shows")
        )
    except (ValueError, SyntaxError):
        old_random_order_shows = []
    
    # Handle changes to random_order_shows
    if old_random_order_shows != settings.random_order_shows and not firstrun:
        # Process newly added random order shows
        for show_id in settings.random_order_shows:
            if show_id not in old_random_order_shows:
                show_name = window.getProperty(f"EasyTV.{show_id}.TVshowTitle")
                if not show_name:
                    # Fallback: lookup from Kodi library if Window property not set yet
                    result = json_query(build_show_details_query(show_id), True)
                    show_name = result.get('tvshowdetails', {}).get('title', 'Unknown')
                log.debug("Adding random order show", show=show_name, show_id=show_id)
                
                # Add to shows_with_next_episodes and shuffle
                if on_add_random_show:
                    on_add_random_show(show_id)
                if on_reshuffle_random_shows:
                    on_reshuffle_random_shows([show_id])
        
        # Process removed random order shows
        for old_show_id in old_random_order_shows:
            if old_show_id not in settings.random_order_shows:
                old_show_name = window.getProperty(f"EasyTV.{old_show_id}.TVshowTitle")
                if not old_show_name:
                    # Fallback: lookup from Kodi library if Window property not set
                    result = json_query(build_show_details_query(old_show_id), True)
                    old_show_name = result.get('tvshowdetails', {}).get('title', 'Unknown')
                log.debug("Removing random order show", show=old_show_name, show_id=old_show_id)
                
                # Check if show has ondeck episodes
                try:
                    has_ondeck = ast.literal_eval(
                        window.getProperty(f"EasyTV.{old_show_id}.ondeck_list")
                    )
                    log.debug("Checking ondeck for removed show", ondeck=has_ondeck)
                except (ValueError, SyntaxError):
                    has_ondeck = False
                
                # If show has ondeck episodes, store next episode before removing
                if has_ondeck:
                    log.debug("Storing ondeck episode for removed random show")
                    retrieved_ondeck_string = window.getProperty(
                        f"EasyTV.{old_show_id}.ondeck_list"
                    )
                    retrieved_offdeck_string = window.getProperty(
                        f"EasyTV.{old_show_id}.offdeck_list"
                    )
                    offdeck_list = ast.literal_eval(retrieved_offdeck_string)
                    ondeck_list = ast.literal_eval(retrieved_ondeck_string)
                    temp_watched_count = int(
                        window.getProperty(f"EasyTV.{old_show_id}.CountWatchedEps")
                        .replace("''", '0')
                    ) + 1
                    temp_unwatched_count = max(
                        0,
                        int(
                            window.getProperty(f"EasyTV.{old_show_id}.CountUnwatchedEps")
                            .replace("''", '0')
                        ) - 1
                    )
                    
                    if on_store_next_ep:
                        on_store_next_ep(
                            ondeck_list[0], old_show_id, ondeck_list, offdeck_list,
                            temp_unwatched_count, temp_watched_count
                        )
                else:
                    if on_remove_show:
                        on_remove_show(old_show_id)
    
    # Update the stored random_order_shows
    window.setProperty("EasyTV.random_order_shows", str(settings.random_order_shows))
    
    log.debug("Random order shows", shows=settings.random_order_shows)
    
    if firstrun:
        log.info(
            "Settings loaded",
            event="settings.load",
            next_prompt=settings.nextprompt,
            prompt_duration=settings.promptduration,
            previous_check=settings.previous_episode_check,
            notifications=settings.playlist_notifications,
            resume_partials_tv=settings.resume_partials_tv,
            resume_partials_movies=settings.resume_partials_movies,
            maintain_smartplaylist=settings.maintainsmartplaylist,
        )
        
        # Initialize display settings with current values
        init_display_settings(addon)
    else:
        log.info("Settings reloaded", event="settings.reload")
    
    return settings
