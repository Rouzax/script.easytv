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
EasyTV maintains five auto-updated smart playlists:
- All Shows: Every show with an ondeck episode
- Continue Watching: Shows where next episode > 1 (mid-season)
- Start Fresh: Shows where next episode = 1 (any season start)
- Show Premieres: Shows at S01E01 (brand new shows)
- Season Premieres: Shows at S02E01+ (new season of existing show)

These playlists can be used by other addons or skins to display
the user's TV shows organized by watch status.

Format Versioning:
    Playlist format changes (like marker format or XML structure) are tracked
    via a version file. On startup, if the version doesn't match, all playlists
    are deleted and regenerated to ensure consistency.

Batch Mode:
    For bulk operations (startup, library rescan), batch mode can be enabled
    to collect all playlist updates and write them in a single operation per
    playlist file. This reduces individual file writes to just 5.
    
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
        - playlist.version_mismatch (INFO): Format version changed, regenerating
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple
from xml.sax.saxutils import escape

import xbmc
import xbmcvfs

from resources.lib.utils import get_logger, log_timing
from resources.lib.constants import (
    FILE_WRITE_DELAY_MS,
    PLAYLIST_XML_HEADER,
    PLAYLIST_XML_FOOTER,
    PLAYLIST_XML_SHOW_ENTRY,
    PLAYLIST_FORMAT_FILENAME,
    PLAYLIST_ALL_SHOWS,
    PLAYLIST_CONTINUE_WATCHING,
    PLAYLIST_START_FRESH,
    PLAYLIST_SHOW_PREMIERES,
    PLAYLIST_SEASON_PREMIERES,
)


# Module-level logger
log = get_logger('data')

# Video playlist location
_video_playlist_location: Optional[str] = None

# Batch mode state
# When enabled, playlist updates are collected instead of written immediately
_batch_mode: bool = False
# Structure: {playlist_filename: (playlist_name, {show_id: (filename, remove_flag)})}
_batch_updates: Dict[str, Tuple[str, Dict[int, Tuple[str, bool]]]] = {}


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
# Format Version Functions
# =============================================================================

def get_format_file_path() -> str:
    """
    Get the path to the playlist format version file.
    
    The version file is stored in the addon's data directory alongside
    other persistent data like the duration cache.
    
    Returns:
        Filesystem path to playlist_format.json
    """
    addon_data = xbmcvfs.translatePath('special://profile/addon_data/script.easytv/')
    return os.path.join(addon_data, PLAYLIST_FORMAT_FILENAME)


def load_playlist_format_version() -> int:
    """
    Load the playlist format version from the version file.
    
    Returns:
        The stored format version, or 0 if the file doesn't exist or is invalid.
        A return value of 0 indicates playlists need to be regenerated.
    """
    version_path = get_format_file_path()
    try:
        with open(version_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('version', 0)
    except (IOError, OSError, json.JSONDecodeError, KeyError):
        return 0


def save_playlist_format_version(version: int, addon_version: str) -> bool:
    """
    Save the playlist format version to the version file.
    
    Args:
        version: The format version number to save
        addon_version: The addon version string for reference
        
    Returns:
        True if saved successfully, False on error
    """
    version_path = get_format_file_path()
    try:
        # Ensure directory exists
        addon_data = os.path.dirname(version_path)
        if not os.path.exists(addon_data):
            os.makedirs(addon_data)
        
        data = {
            'version': version,
            'addon_version': addon_version
        }
        with open(version_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        log.debug("Playlist format version saved",
                 event="playlist.version_saved",
                 version=version,
                 addon_version=addon_version)
        return True
        
    except (IOError, OSError) as e:
        log.exception("Failed to save playlist format version",
                     event="playlist.version_save_fail",
                     error=str(e))
        return False


def delete_easytv_playlists() -> int:
    """
    Delete all EasyTV smart playlist files.
    
    Used during format migration to ensure clean regeneration of playlists
    in the new format.
    
    Returns:
        Number of playlist files deleted
    """
    playlist_dir = _get_playlist_location()
    playlist_files = [
        PLAYLIST_ALL_SHOWS,
        PLAYLIST_CONTINUE_WATCHING,
        PLAYLIST_START_FRESH,
        PLAYLIST_SHOW_PREMIERES,
        PLAYLIST_SEASON_PREMIERES,
    ]
    
    deleted_count = 0
    for playlist_file in playlist_files:
        playlist_path = os.path.join(playlist_dir, playlist_file)
        try:
            if os.path.exists(playlist_path):
                os.remove(playlist_path)
                deleted_count += 1
                log.debug("Deleted playlist file",
                         event="playlist.deleted",
                         file=playlist_file)
        except (IOError, OSError) as e:
            log.warning("Failed to delete playlist file",
                       event="playlist.delete_fail",
                       file=playlist_file,
                       error=str(e))
    
    log.info("EasyTV playlists deleted for format migration",
            event="playlist.migration_delete",
            deleted_count=deleted_count)
    
    return deleted_count


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
    individual file writes to just 5 (one per playlist file).
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
            
            # Build a dict of existing entries: show_id (as string) -> line content
            # We use string keys because XML markers are strings
            existing_entries: Dict[str, str] = {}
            header_lines = []
            footer_line = ""
            
            header = PLAYLIST_XML_HEADER.format(name=playlist_name)
            footer = PLAYLIST_XML_FOOTER.strip()
            
            for line in all_lines:
                stripped = line.strip()
                # Check if this is a show entry (contains <!--show_id-->)
                if '<!--' in line and '-->' in line and '<rule' in line:
                    # Extract show_id from comment marker
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
            for show_id, (filename, remove) in show_updates.items():
                show_id_str = str(show_id)
                if remove:
                    # Remove the entry
                    existing_entries.pop(show_id_str, None)
                else:
                    # Add or update the entry (escape filename for XML safety)
                    escaped_filename = escape(filename)
                    show_entry = PLAYLIST_XML_SHOW_ENTRY.format(
                        show_id=show_id, filename=escaped_filename
                    )
                    existing_entries[show_id_str] = show_entry
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
    show_id: int,
    filename: str,
    remove: bool = False,
    quiet: bool = False
) -> bool:
    """
    Write or update a single smart playlist file.
    
    Handles creating new files, adding entries, updating existing entries,
    and removing entries. Uses comment markers (<!--show_id-->) to identify
    which line belongs to which show.
    
    The playlist format is Kodi's smart playlist XML (.xsp):
    ```xml
    <?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
    <smartplaylist type="episodes">
        <name>EasyTV - All Shows</name>
        <match>one</match>
        <!--123--><rule field="filename" operator="is">
            <value>episode_filename.mkv</value>
        </rule>
        <order direction="ascending">random</order>
    </smartplaylist>
    ```
    
    Args:
        playlist_filename: Filename for the .xsp file (e.g., "EasyTV - All Shows.xsp")
        playlist_name: Display name for the playlist (shown in Kodi)
        show_id: TV show database ID (used as comment identifier)
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
            123,  # show_id
            "Breaking.Bad.S01E02.mkv"
        )
        
        # Remove a show entry
        write_smart_playlist_file(
            "EasyTV - All Shows.xsp",
            "EasyTV - All Shows",
            123,  # show_id
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
        show_updates[show_id] = (filename, remove)
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
    # Escape filename for XML safety (handles &, <, > characters)
    escaped_filename = escape(filename) if filename else ""
    header = PLAYLIST_XML_HEADER.format(name=playlist_name)
    footer = PLAYLIST_XML_FOOTER
    show_entry = PLAYLIST_XML_SHOW_ENTRY.format(show_id=show_id, filename=escaped_filename)
    show_marker = "<!--%s-->" % show_id
    
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
                     playlist=playlist_name, show_id=show_id, 
                     file=filename if action_taken != 'removed' else None)
        
        return True
        
    except (IOError, OSError):
        log.exception("Playlist write failed",
                      event="playlist.fail",
                      playlist=playlist_name, show_id=show_id)
        return False


def remove_show_from_all_playlists(
    show_id: int,
    all_shows_file: str,
    all_shows_name: str,
    continue_watching_file: str,
    continue_watching_name: str,
    start_fresh_file: str,
    start_fresh_name: str,
    show_premieres_file: str,
    show_premieres_name: str,
    season_premieres_file: str,
    season_premieres_name: str,
    quiet: bool = False
) -> None:
    """
    Remove a show from all EasyTV smart playlists.
    
    Called when a show has no more unwatched episodes (user completed the series).
    
    Args:
        show_id: TV show database ID to remove
        all_shows_file: Filename for "All Shows" playlist
        all_shows_name: Display name for "All Shows" playlist
        continue_watching_file: Filename for "Continue Watching" playlist
        continue_watching_name: Display name for "Continue Watching" playlist
        start_fresh_file: Filename for "Start Fresh" playlist
        start_fresh_name: Display name for "Start Fresh" playlist
        show_premieres_file: Filename for "Show Premieres" playlist
        show_premieres_name: Display name for "Show Premieres" playlist
        season_premieres_file: Filename for "Season Premieres" playlist
        season_premieres_name: Display name for "Season Premieres" playlist
        quiet: If True, suppress debug logging (for bulk operations)
    """
    if not quiet:
        log.debug("Removing show from all playlists", show_id=show_id)
    
    write_smart_playlist_file(all_shows_file, all_shows_name, 
                              show_id, "", remove=True, quiet=quiet)
    write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                              show_id, "", remove=True, quiet=quiet)
    write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                              show_id, "", remove=True, quiet=quiet)
    write_smart_playlist_file(show_premieres_file, show_premieres_name, 
                              show_id, "", remove=True, quiet=quiet)
    write_smart_playlist_file(season_premieres_file, season_premieres_name, 
                              show_id, "", remove=True, quiet=quiet)
    
    if not quiet:
        log.debug("Show removed from all playlists", show_id=show_id)


def update_show_in_playlists(
    show_id: int,
    filename: str,
    category: str,
    premiere_category: str,
    all_shows_file: str,
    all_shows_name: str,
    continue_watching_file: str,
    continue_watching_name: str,
    start_fresh_file: str,
    start_fresh_name: str,
    show_premieres_file: str,
    show_premieres_name: str,
    season_premieres_file: str,
    season_premieres_name: str,
    category_start_fresh: str,
    category_show_premiere: str,
    category_season_premiere: str,
    episodeno: str = "",
    quiet: bool = False
) -> None:
    """
    Update a show's entry across all EasyTV smart playlists.
    
    Adds/updates the show in "All Shows" and the appropriate category playlists,
    while removing it from inapplicable playlists (in case show moved categories).
    
    Args:
        show_id: TV show database ID
        filename: Episode filename for the playlist rule
        category: Category identifier (CATEGORY_START_FRESH or CATEGORY_CONTINUE_WATCHING)
        premiere_category: Premiere type (CATEGORY_SHOW_PREMIERE, CATEGORY_SEASON_PREMIERE, or empty)
        all_shows_file: Filename for "All Shows" playlist
        all_shows_name: Display name for "All Shows" playlist
        continue_watching_file: Filename for "Continue Watching" playlist
        continue_watching_name: Display name for "Continue Watching" playlist
        start_fresh_file: Filename for "Start Fresh" playlist
        start_fresh_name: Display name for "Start Fresh" playlist
        show_premieres_file: Filename for "Show Premieres" playlist
        show_premieres_name: Display name for "Show Premieres" playlist
        season_premieres_file: Filename for "Season Premieres" playlist
        season_premieres_name: Display name for "Season Premieres" playlist
        category_start_fresh: The constant value for CATEGORY_START_FRESH
        category_show_premiere: The constant value for CATEGORY_SHOW_PREMIERE
        category_season_premiere: The constant value for CATEGORY_SEASON_PREMIERE
        episodeno: Episode number string for logging (optional)
        quiet: If True, suppress debug logging (for bulk operations)
    """
    if not quiet:
        log.debug("Updating smart playlists",
                 show_id=show_id, episode=episodeno, category=category,
                 premiere_category=premiere_category)
    
    # Always write to "All Shows"
    write_smart_playlist_file(all_shows_file, all_shows_name, show_id, filename,
                              quiet=quiet)
    
    # Write to appropriate category playlist and remove from opposite
    if category == category_start_fresh:
        write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                                  show_id, filename, quiet=quiet)
        # Remove from Continue Watching (in case show moved categories)
        write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                                  show_id, filename, remove=True, quiet=quiet)
    else:
        write_smart_playlist_file(continue_watching_file, continue_watching_name, 
                                  show_id, filename, quiet=quiet)
        # Remove from Start Fresh (in case show moved categories)
        write_smart_playlist_file(start_fresh_file, start_fresh_name, 
                                  show_id, filename, remove=True, quiet=quiet)
    
    # Handle premiere playlists
    if premiere_category == category_show_premiere:
        # S01E01 - Show Premiere
        write_smart_playlist_file(show_premieres_file, show_premieres_name, 
                                  show_id, filename, quiet=quiet)
        # Remove from Season Premieres (in case show moved)
        write_smart_playlist_file(season_premieres_file, season_premieres_name, 
                                  show_id, filename, remove=True, quiet=quiet)
    elif premiere_category == category_season_premiere:
        # S02E01+ - Season Premiere
        write_smart_playlist_file(season_premieres_file, season_premieres_name, 
                                  show_id, filename, quiet=quiet)
        # Remove from Show Premieres (in case show moved)
        write_smart_playlist_file(show_premieres_file, show_premieres_name, 
                                  show_id, filename, remove=True, quiet=quiet)
    else:
        # Not a premiere (episode > 1) - remove from both premiere playlists
        write_smart_playlist_file(show_premieres_file, show_premieres_name, 
                                  show_id, filename, remove=True, quiet=quiet)
        write_smart_playlist_file(season_premieres_file, season_premieres_name, 
                                  show_id, filename, remove=True, quiet=quiet)
    
    if not quiet:
        log.debug("Smart playlists updated",
                 show_id=show_id, episode=episodeno, category=category)
