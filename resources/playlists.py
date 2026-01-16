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
Playlist Selection Dialog for EasyTV

This module provides a simple dialog for selecting a video smart playlist
from the user's Kodi profile. It is invoked from the EasyTV settings
when the user wants to set a default playlist for filtering TV shows.

The selected playlist path is saved to the 'user_playlist_path' setting and can
be used to filter which shows appear in EasyTV features.
"""

import os
import xbmcaddon
import xbmcgui

# Import shared utilities
from resources.lib.utils import lang, json_query

__addon__ = xbmcaddon.Addon('script.easytv')
__addonid__ = __addon__.getAddonInfo('id')

plf = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", "params": {"directory": "special://profile/playlists/video/", "media": "video"}}

def playlist_selection_window():
    ''' Purpose: launch Select Window populated with smart playlists '''

    result = json_query(plf, True)
    playlist_files = result.get('files') if result else None

    if playlist_files:

        plist_files = dict((x['label'], x['file']) for x in playlist_files)

        playlist_list = sorted(plist_files.keys())

        inputchoice = xbmcgui.Dialog().select(lang(32104, __addonid__), playlist_list)

        # Handle user cancellation (inputchoice == -1)
        if inputchoice < 0:
            return 'empty'
        
        return plist_files[playlist_list[inputchoice]]
    else:
        return 'empty'


pl = playlist_selection_window()

# Only save if user made a valid selection
# With <close>true</close>, settings dialog is already closed so we can use setSetting directly
if pl != 'empty':
    __addon__.setSetting(id="user_playlist_path", value=pl)
    # Update display setting with filename only
    filename = os.path.basename(pl)
    if filename.endswith('.xsp'):
        filename = filename[:-4]
    __addon__.setSetting(id="playlist_file_display", value=filename)

__addon__.openSettings()
