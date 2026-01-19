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

Batch Mode:
    For bulk operations (startup, library rescan), batch mode can be enabled
    to collect all playlist updates and write them in a single operation per
    playlist file. This reduces 831 individual file writes to just 3.
    
    Usage:
        start_playlist_batch()
        # ... perform many playlist updates ...
        flush_playlist_batch()

Logging:
    Logger: 'data' (via get_logger)
    Key events:
        - playlist.write (DEBUG): Playlist file written
        - playlist.fail (ERROR): Playlist write failed
        - playlist.batch_flush (DEBUG): Batch mode flushed
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import os

import xbmc
import xbmcvfs

from resources.lib.utils import get_logger, log_timing
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

# Batch mode state
# When enabled, playlist updates are collected instead of written immediately
_batch_mode: bool = False
# Structure: {playlist_filename: (playlist_name, {showname: (filename, remove_flag)})}
_batch_updates: Dict[str, Tuple[str, Dict[str, Tuple[str, bool]]]] = {}


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


# =============================================================================
# Batch Mode Functions
# =============================================================================

def start_playlist_batch() -> None:
    """
    Enable batch mode for playlist updates.
    
    When batch mode is enabled, calls to write_smart_playlist_file() will
    collect updates in memory instead of writing to disk immediately.
    Call flush_playlist_batch() to write all collected updates at once.
    
    This significantly improves performance for bulk operations by reducing
    831 individual file writes to just 3 (one per playlist file).
    """
    global _batch_mode, _batch_updates
    _batch_mode = True
    _batch_updates = {}
    log.debug("Playlist batch mode started")


def flush_playlist_batch() -> None:
    """
    Write all collected playlist updates and disable batch mode.
    
    Reads each playlist file once, applies all pending changes for that file,
    and writes it back. This is much more efficient than individual writes.
    
    After flushing, batch mode is disabled and subsequent updates will
    be written immediately as normal.
    """
    global _batch_mode, _batch_updates
    
    if not _batch_mode:
        return
    
    with log_timing(log, "playlist_batch_flush"):
        files_written = 0
        shows_updated = 0
        
        for playlist_filename, (playlist_name, show_updates) in _batch_updates.items():
            if not show_updates:
                continue
            
            playlist_path = os.path.join(_get_playlist_location(), playlist_filename)
            
            # Read existing file contents
            try:
                with open(playlist_path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
            except (IOError, OSError):
                all_lines = []
            
            # Build a dict of existing entries: showname -> line content
            existing_entries: Dict[str, str] = {}
            header_lines = []
            footer_line = ""
            
            header = PLAYLIST_XML_HEADER.format(name=playlist_name)
            footer = PLAYLIST_XML_FOOTER.strip()
            
            for line in all_lines:
                stripped = line.strip()
                # Check if this is a show entry (contains <!--ShowName-->)
                if '<!--' in line and '-->' in line and '<rule' in line:
                    # Extract show name from comment marker
                    start = line.find('<!--') + 4
                    end = line.find('-->', start)
                    if start > 3 and end > start:
                        show_marker = line[start:end]
                        existing_entries[show_marker] = line
                elif stripped == footer:
                    footer_line = line
                elif stripped and not existing_entries:
                    # Header lines (before any entries)
                    header_lines.append(line)
            
            # Apply updates
            for showname, (filename, remove) in show_updates.items():
                if remove:
                    # Remove the entry
                    existing_entries.pop(showname, None)
                else:
                    # Add or update the entry
                    show_entry = PLAYLIST_XML_SHOW_ENTRY.format(show=showname, filename=filename)
                    existing_entries[showname] = show_entry
                shows_updated += 1
            
            # Write the file
            try:
                # Small delay before file write (single delay per file, not per entry)
                xbmc.sleep(FILE_WRITE_DELAY_MS)
                
                with open(playlist_path, 'w+', encoding='utf-8') as f:
                    # Write header (use existing or create new)
                    if header_lines:
                        f.write(''.join(header_lines))
                    else:
                        f.write(header)
                    
                    # Write all entries
                    for entry in existing_entries.values():
                        f.write(entry)
                    
                    # Write footer
                    f.write(footer_line if footer_line else PLAYLIST_XML_FOOTER)
                
                files_written += 1
                
            except (IOError, OSError):
                log.exception("Batch playlist write failed",
                             event="playlist.fail",
                             playlist=playlist_name)
        
        log.debug("Playlist batch metrics",
                 event="playlist.batch_flush",
                 files_written=files_written,
                 shows_updated=shows_updated)
    
    # Reset batch state
    _batch_mode = False
    _batch_updates = {}


def write_smart_playlist_file(
    playlist_filename: str,
    playlist_name: str,
    showname: str,
    filename: str,
    remove: bool = False,
    quiet: bool = False
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
        quiet: If True, suppress debug logging (for bulk operations)
    
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
    # In batch mode, collect updates instead of writing immediately
    if _batch_mode:
        # Initialize playlist entry if not exists
        if playlist_filename not in _batch_updates:
            _batch_updates[playlist_filename] = (playlist_name, {})
        
        # Store the update (later updates for same show overwrite earlier ones)
        _, show_updates = _batch_updates[playlist_filename]
        show_updates[showname] = (filename, remove)
        return True
    
    # Non-batch mode: immediate write (existing behavior)
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
        
        # Log the action taken (only if something actually happened and not in quiet mode)
        if action_taken and not quiet:
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
    start_fresh_name: str,
    quiet: bool = False
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
        quiet: If True, suppress debug logging (for bulk operations)
    """
    if not quiet:
        log.debug("Removing show from all playlists", show=showname)
    
    write_smart_playlist_file(all_shows_file, all_shows_name, 
                              showname, "", remove=True, quiet=quiet)
    write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                              showname, "", remove=True, quiet=quiet)
    write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                              showname, "", remove=True, quiet=quiet)
    
    if not quiet:
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
    episodeno: str = "",
    quiet: bool = False
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
        quiet: If True, suppress debug logging (for bulk operations)
    """
    if not quiet:
        log.debug("Updating smart playlists",
                 show=showname, episode=episodeno, category=category)
    
    # Always write to "All Shows"
    write_smart_playlist_file(all_shows_file, all_shows_name, showname, filename,
                              quiet=quiet)
    
    # Write to appropriate category playlist and remove from opposite
    if category == category_start_fresh:
        write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                                  showname, filename, quiet=quiet)
        # Remove from Continue Watching (in case show moved categories)
        write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                                  showname, filename, remove=True, quiet=quiet)
    else:
        write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                                  showname, filename, quiet=quiet)
        # Remove from Start Fresh (in case show moved categories)
        write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                                  showname, filename, remove=True, quiet=quiet)
    
    if not quiet:
        log.debug("Smart playlists updated",
                 show=showname, episode=episodeno, category=category)
