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
EasyTV Episode List Builder.

Builds and displays an episode list window for browsing TV shows.
Users can view next unwatched episodes for all shows, select episodes
for playback, and interact via context menu options.

Extracted from default.py as part of modularization.

Logging:
    Logger: 'playback' (via get_logger)
    Key events:
        - playback.list_open (DEBUG): Episode list window opened
        - playback.list_select (DEBUG): Episode selected from list
        - playback.list_close (DEBUG): Episode list window closed
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

import xbmc
import xbmcgui

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    KODI_FULLSCREEN_VIDEO_WINDOW_ID,
    MAIN_LOOP_SLEEP_MS,
    PLAYLIST_ADD_DELAY_MS,
    DIALOG_WAIT_SLEEP_MS,
    DIALOG_WAIT_MAX_TICKS,
)
from resources.lib.data.queries import (
    get_clear_video_playlist_query,
    build_add_episode_query,
)
from resources.lib.utils import get_logger, json_query
from resources.lib.ui.browse_window import (
    BrowseWindow, BrowseWindowConfig, get_skin_xml_file
)
from resources.lib.playback.browse_player import BrowseModePlayer

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


@dataclass
class EpisodeListConfig:
    """
    Configuration for the episode list builder.
    
    Attributes:
        skin: Skin style (0=DialogSelect, 1=main, 2=BigScreenList)
        limit_shows: Whether to limit the number of shows displayed
        window_length: Maximum number of shows when limit_shows is True
        skin_return: Whether to return to the window after playback
        excl_random_order_shows: Whether to exclude random-order shows
        script_path: Path to the addon for locating resources
    """
    skin: int = 0
    limit_shows: bool = False
    window_length: int = 20
    skin_return: bool = True
    excl_random_order_shows: bool = False
    script_path: str = ''


def build_episode_list(
    show_data: list,
    random_order_shows: list,
    config: EpisodeListConfig,
    monitor: Optional[xbmc.Monitor] = None,
    logger: Optional[StructuredLogger] = None
) -> None:
    """
    Build and display an episode list window for browsing TV shows.
    
    Creates a browse window showing next unwatched episodes for all shows
    (or a filtered subset). Users can select episodes for playback,
    use context menu options, and interact with the list.
    
    The function runs a modal loop until the user closes the window or
    Kodi requests abort.
    
    Args:
        show_data: List of show data [[lastplayed, showid, episodeid], ...]
                   typically from process_stored() or fetch_unwatched_shows()
        random_order_shows: List of show IDs marked for random ordering
        config: EpisodeListConfig with display and behavior settings
        monitor: Optional xbmc.Monitor for abort checking (creates one if None)
        logger: Optional logger instance (uses module logger if None)
    
    Side Effects:
        - Sets 'EasyTV.playlist_running' property when playback starts
        - Sets 'EasyTV.random_order_shuffle' property to trigger reshuffling
        - Starts video playlist playback when user selects episodes
    
    Example:
        ```python
        config = EpisodeListConfig(
            skin=1,
            limit_shows=True,
            window_length=25,
            script_path='/path/to/addon'
        )
        show_data = process_stored({'none': ''})
        build_episode_list(show_data, [], config)
        ```
    """
    log = logger or _get_log()
    mon = monitor or xbmc.Monitor()
    
    log.debug("Building episode list")
    
    # Filter out random-order shows if configured
    if config.excl_random_order_shows and random_order_shows:
        filtered_data = [x for x in show_data if x[1] not in random_order_shows]
    else:
        filtered_data = show_data
    
    # Get appropriate XML file for skin
    xmlfile = get_skin_xml_file(config.skin)
    
    # Create browse window configuration
    browse_config = BrowseWindowConfig(
        skin=config.skin,
        limit_shows=config.limit_shows,
        window_length=config.window_length,
        skin_return=config.skin_return
    )
    
    # Create the browse window
    list_window = BrowseWindow(
        xmlfile, config.script_path, 'Default',
        data=filtered_data,
        config=browse_config,
        script_path=config.script_path,
        logger=log
    )
    
    # Create player that coordinates with the window
    player = BrowseModePlayer(parent=list_window)
    
    # Main UI loop
    stay_open = True
    open_window = True
    
    while stay_open and not mon.abortRequested():
        
        if open_window:
            log.debug("Opening episode list window", 
                     existing_window=xbmc.getInfoLabel('Window.Property(xmlfile)'))
            
            # Wait for any existing dialogs to close
            # This prevents the window from covering YesNo dialogs from the service
            count = 0
            while count < DIALOG_WAIT_MAX_TICKS or \
                  xbmc.getInfoLabel('Window.Property(xmlfile)') == 'DialogYesNo.xml':
                xbmc.sleep(DIALOG_WAIT_SLEEP_MS)
                count += 1
            
            open_window = False
            list_window.doModal()
        
        # Check window state after modal closes
        if list_window.should_close:
            stay_open = False
            continue
        
        if list_window.needs_refresh:
            open_window = True
            list_window.reset_state()
            continue
        
        selected = list_window.selected_show
        
        if selected != 'null' and list_window.play_requested:
            log.debug("Starting playback from episode list")
            
            # Mark playlist as running in listview mode
            WINDOW.setProperty("EasyTV.playlist_running", 'listview')
            
            # Clear and rebuild playlist
            # This approach is needed because .strm files won't start via JSON-RPC
            json_query(get_clear_video_playlist_query(), False)
            
            # Add selected episode(s) to playlist
            try:
                # Multiple episodes selected
                for ep in selected:
                    json_query(build_add_episode_query(int(ep)), False)
            except TypeError:
                # Single episode selected
                json_query(build_add_episode_query(int(selected)), False)
            
            # Start playback
            xbmc.sleep(PLAYLIST_ADD_DELAY_MS)
            player.play(xbmc.PlayList(1))
            xbmc.executebuiltin('ActivateWindow(%d)' % KODI_FULLSCREEN_VIDEO_WINDOW_ID)
            
            # Reset for next iteration
            list_window.reset_state()
            
            # Notify service to reshuffle random order shows
            WINDOW.setProperty("EasyTV.random_order_shuffle", 'true')
        
        # Check if we should stay open after playback
        if not config.skin_return:
            stay_open = False
        
        xbmc.sleep(MAIN_LOOP_SLEEP_MS)
    
    # Cleanup
    del list_window
    del player
    
    # Final notification to service
    WINDOW.setProperty("EasyTV.random_order_shuffle", 'true')
    
    log.debug("Episode list closed")
