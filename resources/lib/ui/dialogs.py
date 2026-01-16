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
EasyTV Dialog Helpers.

Provides common dialog functions used throughout the addon:
- show_error_and_exit: Display error and gracefully exit
- show_playlist_selection: Present smart playlist chooser

Extracted from default.py as part of modularization.

Logging:
    Logger: 'ui' (via get_logger)
    Key events:
        - ui.dialog_open (DEBUG): Dialog opened
        - ui.dialog_select (DEBUG): User made selection
        - ui.dialog_cancel (DEBUG): User cancelled dialog
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import sys
from typing import Optional, TYPE_CHECKING

import xbmcgui

from resources.lib.utils import get_logger, json_query, lang
from resources.lib.data.queries import get_playlist_files_query

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# Module-level logger (initialized lazily)
_log: Optional[StructuredLogger] = None


def _get_log() -> StructuredLogger:
    """Get or create the module logger."""
    global _log
    if _log is None:
        _log = get_logger('ui')
    return _log


def show_error_and_exit(
    message: str,
    title: str = "EasyTV",
    dialog: Optional[xbmcgui.Dialog] = None,
) -> None:
    """
    Display an error dialog and exit the addon gracefully.
    
    Shows a modal OK dialog with the error message, then terminates
    the addon script. Use this for fatal errors that prevent the
    addon from functioning.
    
    Args:
        message: The error message to display.
        title: Dialog title (defaults to "EasyTV").
        dialog: Optional Dialog instance. If None, creates one.
    
    Note:
        This function does not return - it calls sys.exit().
    """
    if dialog is None:
        dialog = xbmcgui.Dialog()
    
    dialog.ok(title, message)
    sys.exit()


def show_playlist_selection(
    dialog: Optional[xbmcgui.Dialog] = None,
    logger: Optional[StructuredLogger] = None,
) -> str:
    """
    Launch a selection dialog populated with video smart playlists.
    
    Queries Kodi for all video playlists in the playlists directory
    and presents them in a selection dialog for the user to choose.
    
    Args:
        dialog: Optional Dialog instance. If None, creates one.
        logger: Optional logger instance. If None, uses module logger.
    
    Returns:
        The file path of the selected playlist, or 'empty' if:
        - No playlists found
        - User cancelled the dialog
    """
    log = logger or _get_log()
    
    if dialog is None:
        dialog = xbmcgui.Dialog()
    
    log.debug("Playlist selection dialog opening")
    
    # Query Kodi for available playlists
    result = json_query(get_playlist_files_query(), True)
    playlist_files = result.get('files') if result else None
    
    if not playlist_files:
        log.debug("No playlists found")
        return 'empty'
    
    # Build dict for label -> file path mapping
    playlist_file_dict = {
        item['label']: item['file'] 
        for item in playlist_files
    }
    playlist_list = sorted(playlist_file_dict.keys())
    
    log.debug("Playlist selection dialog displayed", count=len(playlist_list))
    
    # Show selection dialog
    # lang(32104) = "Select Playlist"
    input_choice = dialog.select(lang(32104), playlist_list)
    
    # Handle user cancellation (input_choice == -1)
    if input_choice < 0:
        log.debug("Playlist selection cancelled by user")
        return 'empty'
    
    selected_playlist = playlist_file_dict[playlist_list[input_choice]]
    log.debug("Playlist selection made", playlist=selected_playlist)
    
    return selected_playlist
