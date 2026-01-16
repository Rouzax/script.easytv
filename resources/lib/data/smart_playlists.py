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
Smart Playlist File I/O for EasyTV.

This module handles reading and writing of Kodi smart playlist (.xsp) files.
EasyTV maintains three auto-updated smart playlists:
- All Shows: Every show with an ondeck episode
- Continue Watching: Shows where next episode > 1 (mid-season)
- Start Fresh: Shows where next episode = 1 (season start)

These playlists can be used by other addons or skins to display
the user's TV shows organized by watch status.

Logging:
    Logger: 'data' (via get_logger)
    Key events:
        - playlist.write (DEBUG): Playlist file written
        - playlist.fail (ERROR): Playlist write failed
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Optional

import os

import xbmc
import xbmcvfs

from resources.lib.utils import get_logger
from resources.lib.constants import (
    FILE_WRITE_DELAY_MS,
    PLAYLIST_XML_HEADER,
    PLAYLIST_XML_FOOTER,
    PLAYLIST_XML_SHOW_ENTRY,
)


# Module-level logger
log = get_logger('data')

# Video playlist location
_video_playlist_location: Optional[str] = None


def _get_playlist_location() -> str:
    """
    Get the video playlist directory path.
    
    Lazily initializes and caches the translated path.
    
    Returns:
        Filesystem path to special://profile/playlists/video/
    """
    global _video_playlist_location
    if _video_playlist_location is None:
        _video_playlist_location = xbmcvfs.translatePath(
            'special://profile/playlists/video/'
        )
    return _video_playlist_location


def write_smart_playlist_file(
    playlist_filename: str,
    playlist_name: str,
    showname: str,
    filename: str,
    remove: bool = False
) -> bool:
    """
    Write or update a single smart playlist file.
    
    Handles creating new files, adding entries, updating existing entries,
    and removing entries. Uses comment markers (<!--ShowName-->) to identify
    which line belongs to which show.
    
    The playlist format is Kodi's smart playlist XML (.xsp):
    ```xml
    <?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
    <smartplaylist type="episodes">
        <name>EasyTV - All Shows</name>
        <match>one</match>
        <!--Show Name--><rule field="filename" operator="is">
            <value>episode_filename.mkv</value>
        </rule><!--END-->
        <order direction="ascending">random</order>
    </smartplaylist>
    ```
    
    Args:
        playlist_filename: Filename for the .xsp file (e.g., "EasyTV - All Shows.xsp")
        playlist_name: Display name for the playlist (shown in Kodi)
        showname: TV show name (used as comment identifier)
        filename: Episode filename for the rule
        remove: If True, remove the show entry instead of adding/updating
    
    Returns:
        True if operation succeeded, False on error
    
    Examples:
        # Add/update a show entry
        write_smart_playlist_file(
            "EasyTV - All Shows.xsp",
            "EasyTV - All Shows",
            "Breaking Bad",
            "Breaking.Bad.S01E02.mkv"
        )
        
        # Remove a show entry
        write_smart_playlist_file(
            "EasyTV - All Shows.xsp",
            "EasyTV - All Shows",
            "Breaking Bad",
            "",
            remove=True
        )
    """
    playlist_path = os.path.join(_get_playlist_location(), playlist_filename)
    
    # Read existing file contents
    try:
        with open(playlist_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
    except (IOError, OSError):
        all_lines = []
    
    # Prepare XML components using constants
    header = PLAYLIST_XML_HEADER.format(name=playlist_name)
    footer = PLAYLIST_XML_FOOTER
    show_entry = PLAYLIST_XML_SHOW_ENTRY.format(show=showname, filename=filename)
    show_marker = "<!--%s-->" % showname
    
    content = []
    found = False
    action_taken = None  # Track what action was performed for logging
    
    # Small delay before file write
    xbmc.sleep(FILE_WRITE_DELAY_MS)
    
    try:
        with open(playlist_path, 'w+', encoding='utf-8') as f:
            # Create new file if empty
            if not all_lines:
                if not remove and filename:
                    content.append(header)
                    content.append(show_entry)
                    content.append(footer)
                    action_taken = 'created'
                # else: removing from non-existent file, nothing to do
            else:
                # Process existing file line by line
                for line in all_lines:
                    # Found the show's entry
                    if show_marker in line:
                        found = True
                        if filename and not remove:
                            # Update existing entry
                            content.append(show_entry)
                            action_taken = 'updated'
                        else:
                            # Removing - don't append (entry deleted)
                            action_taken = 'removed'
                        continue
                    
                    # Last line (footer) and show not found yet
                    if not found and line.strip() == footer.strip() and not remove:
                        if filename:
                            # Add new entry before footer
                            content.append(show_entry)
                            action_taken = 'added'
                        content.append(line)
                    else:
                        # Keep existing line
                        content.append(line)
            
            # Write content
            f.write(''.join(content))
        
        # Log the action taken (only if something actually happened)
        if action_taken:
            log.debug("Playlist entry %s" % action_taken,
                     playlist=playlist_name, show=showname, 
                     file=filename if action_taken != 'removed' else None)
        
        return True
        
    except (IOError, OSError):
        log.exception("Playlist write failed",
                      event="playlist.fail",
                      playlist=playlist_name, show=showname)
        return False


def remove_show_from_all_playlists(
    showname: str,
    all_shows_file: str,
    all_shows_name: str,
    continue_watching_file: str,
    continue_watching_name: str,
    start_fresh_file: str,
    start_fresh_name: str
) -> None:
    """
    Remove a show from all EasyTV smart playlists.
    
    Called when a show has no more unwatched episodes (user completed the series).
    
    Args:
        showname: TV show name to remove
        all_shows_file: Filename for "All Shows" playlist
        all_shows_name: Display name for "All Shows" playlist
        continue_watching_file: Filename for "Continue Watching" playlist
        continue_watching_name: Display name for "Continue Watching" playlist
        start_fresh_file: Filename for "Start Fresh" playlist
        start_fresh_name: Display name for "Start Fresh" playlist
    """
    log.debug("Removing show from all playlists", show=showname)
    
    write_smart_playlist_file(all_shows_file, all_shows_name, 
                              showname, "", remove=True)
    write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                              showname, "", remove=True)
    write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                              showname, "", remove=True)
    
    log.debug("Show removed from all playlists", show=showname)


def update_show_in_playlists(
    showname: str,
    filename: str,
    category: str,
    all_shows_file: str,
    all_shows_name: str,
    continue_watching_file: str,
    continue_watching_name: str,
    start_fresh_file: str,
    start_fresh_name: str,
    category_start_fresh: str,
    episodeno: str = ""
) -> None:
    """
    Update a show's entry across all EasyTV smart playlists.
    
    Adds/updates the show in "All Shows" and the appropriate category playlist,
    while removing it from the opposite category playlist (in case it moved).
    
    Args:
        showname: TV show name
        filename: Episode filename for the playlist rule
        category: Category identifier (CATEGORY_START_FRESH or CATEGORY_CONTINUE_WATCHING)
        all_shows_file: Filename for "All Shows" playlist
        all_shows_name: Display name for "All Shows" playlist
        continue_watching_file: Filename for "Continue Watching" playlist
        continue_watching_name: Display name for "Continue Watching" playlist
        start_fresh_file: Filename for "Start Fresh" playlist
        start_fresh_name: Display name for "Start Fresh" playlist
        category_start_fresh: The constant value for CATEGORY_START_FRESH
        episodeno: Episode number string for logging (optional)
    """
    log.debug("Updating smart playlists",
             show=showname, episode=episodeno, category=category)
    
    # Always write to "All Shows"
    write_smart_playlist_file(all_shows_file, all_shows_name, showname, filename)
    
    # Write to appropriate category playlist and remove from opposite
    if category == category_start_fresh:
        write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                                  showname, filename)
        # Remove from Continue Watching (in case show moved categories)
        write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                                  showname, filename, remove=True)
    else:
        write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                                  showname, filename)
        # Remove from Start Fresh (in case show moved categories)
        write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                                  showname, filename, remove=True)
    
    log.debug("Smart playlists updated",
             show=showname, episode=episodeno, category=category)
