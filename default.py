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
EasyTV Main Entry Point - UI for browsing episodes and creating random playlists.

Modernized for Kodi 21+ (Nexus/Omega).

Logging:
    Module: default
    Events:
        - ui.start (INFO): Addon UI started
        - ui.stop (INFO): Addon UI finished
        - playlist.save (INFO): Playlist saved to file
        - version.mismatch (WARNING): Addon/service version mismatch
        - clone.outdated (WARNING): Clone addon needs update
        - service.missing (WARNING): EasyTV service not running
"""

import ast
import sys

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID, ADDON_RESTART_DELAY_MS,
    SERVICE_POLL_SLEEP_MS, SERVICE_POLL_TIMEOUT_TICKS,
)
from resources.lib.utils import (
    lang, get_logger, get_bool_setting, get_int_setting, get_float_setting
)
from resources.lib.ui.dialogs import show_playlist_selection
from resources.lib.playback.episode_list import EpisodeListConfig, build_episode_list
from resources.lib.playback.random_player import (
    RandomPlaylistConfig, filter_shows_by_population, build_random_playlist
)


def _get_population(filter_enabled, populate_by, playlist_source,
                    user_playlist_path, selected_shows, dialog, log):
    """Build population filter based on settings."""
    if not filter_enabled:
        return {'none': ''}
    if populate_by == '1':
        if playlist_source == '0':
            return {'playlist': show_playlist_selection(dialog=dialog, logger=log)}
        return {'playlist': user_playlist_path} if user_playlist_path else {'none': ''}
    return {'usersel': selected_shows}


def _get_skin_setting(addon):
    """Get skin style setting, handling legacy values."""
    view_style = addon.getSetting('view_style')
    if view_style == 'true':
        addon.setSetting('view_style', '1')
        return 1
    if view_style in ('false', '32073'):
        addon.setSetting('view_style', '1')
        return 0
    try:
        return int(view_style)
    except (ValueError, TypeError):
        return 0


def main_entry(addon, log):
    """Main entry point - determines mode and launches appropriate functionality."""
    log.debug("Main entry point")

    dialog = xbmcgui.Dialog()
    window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    script_path = addon.getAddonInfo('path')

    # Load settings
    primary_function = addon.getSetting('primary_function')
    filter_enabled = get_bool_setting('filter_enabled')
    sort_by = get_int_setting('sort_by')
    sort_reverse = get_bool_setting('sort_reverse')

    try:
        selected_shows = ast.literal_eval(addon.getSetting('selection'))
    except (ValueError, SyntaxError):
        selected_shows = []

    try:
        random_order_shows = ast.literal_eval(window.getProperty("EasyTV.random_order_shows"))
    except (ValueError, SyntaxError):
        random_order_shows = []

    population = _get_population(
        filter_enabled, addon.getSetting('populate_by'),
        addon.getSetting('playlist_source'), addon.getSetting('user_playlist_path'),
        selected_shows, dialog, log
    )

    # Determine mode: 0=browse, 1=random playlist, 2=ask
    if primary_function == '2':
        choice = dialog.yesno('EasyTV', lang(32100) + '\n\n' + lang(32101),
                              nolabel=lang(32102), yeslabel=lang(32103))
        if choice < 0:
            sys.exit()
    else:
        choice = int(primary_function) if primary_function in ('0', '1') else 0

    language = xbmc.getInfoLabel('System.Language')

    if choice == 1:
        # Random playlist mode
        build_random_playlist(
            population=population,
            random_order_shows=random_order_shows,
            config=RandomPlaylistConfig(
                length=get_int_setting('length'),
                playlist_content=get_int_setting('playlist_content'),
                movie_selection=get_int_setting('movie_selection'),
                movieweight=get_float_setting('movieweight'),
                start_partials=get_bool_setting('start_partials'),
                premieres=get_bool_setting('premieres'),
                multiple_shows=get_bool_setting('multiple_shows'),
                sort_by=sort_by, sort_reverse=sort_reverse, language=language
            ),
            logger=log
        )
    else:
        # Browse mode
        show_data = filter_shows_by_population(population, sort_by, sort_reverse, language, log)
        
        # Filter out premieres (S01E01) if setting is disabled
        if not get_bool_setting('premieres'):
            show_data = [x for x in show_data 
                         if window.getProperty(f"EasyTV.{x[1]}.EpisodeNo") != 's01e01']
        
        build_episode_list(
            show_data=show_data,
            random_order_shows=random_order_shows,
            config=EpisodeListConfig(
                skin=_get_skin_setting(addon),
                limit_shows=get_bool_setting('limit_shows'),
                window_length=get_int_setting('window_length'),
                skin_return=get_bool_setting('skin_return'),
                excl_random_order_shows=get_bool_setting('excl_random_order_shows'),
                script_path=script_path
            ),
            monitor=xbmc.Monitor(),
            logger=log
        )


def _handle_special_modes(mode, addon, log):
    """Handle special invocation modes (from settings actions)."""
    import os

    if mode == 'playlist':
        log.debug("Playlist selection mode")
        pl = show_playlist_selection(dialog=xbmcgui.Dialog(), logger=log)
        if pl != 'empty':
            # With <close>true</close>, settings dialog is already closed
            # so we can use setSetting() directly
            addon.setSetting(id="user_playlist_path", value=pl)
            # Update display setting with filename only
            filename = os.path.basename(pl)
            if filename.endswith('.xsp'):
                filename = filename[:-4]
            addon.setSetting(id="playlist_file_display", value=filename)
            log.info("Playlist saved", event="playlist.save", path=pl, display=filename)
        
        # Force-close any lingering dialog instances to prevent stale cache
        # Then reopen settings as a fresh instance after a short delay
        # Note: Using 00:01 (MM:SS) format for AlarmClock compatibility
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            'AlarmClock(EasyTVSettings,Addon.OpenSettings(script.easytv),00:01,silent)'
        )

    elif mode == 'selector':
        log.debug("Selector mode")
        from resources import selector
        _ = selector  # Import runs selector at module level
        
        # Force-close any lingering dialog instances to prevent stale cache
        # Then reopen settings as a fresh instance after a short delay
        # Note: Using 00:01 (MM:SS) format for AlarmClock compatibility
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            'AlarmClock(EasyTVSettings,Addon.OpenSettings(script.easytv),00:01,silent)'
        )

    elif mode == 'clone':
        log.debug("Clone creation mode")
        from resources import clone
        clone.Main()

    elif mode == 'exporter':
        log.debug("Exporter mode")
        from resources import episode_exporter
        episode_exporter.Main()


def _check_service_running(window, log):
    """Check if EasyTV service is running. Returns True if running."""
    window.setProperty('EasyTV_service_running', 'marco')
    count = 0
    while window.getProperty('EasyTV_service_running') == 'marco':
        count += 1
        if count > SERVICE_POLL_TIMEOUT_TICKS:
            return False
        xbmc.sleep(SERVICE_POLL_SLEEP_MS)
    return True


def _handle_version_mismatch(addon_version, addon_id, script_path, script_name, window, dialog, log):
    """Check version compatibility. Returns True if OK to proceed."""
    try:
        service_version = ast.literal_eval(window.getProperty("EasyTV.Version"))
    except (ValueError, SyntaxError):
        service_version = (0, 0, 0)

    if addon_version != service_version and addon_id == "script.easytv":
        log.warning("Version mismatch", event="version.mismatch", 
                    addon_version=addon_version, service_version=service_version)
        dialog.ok('EasyTV', lang(32108))
        return False

    if addon_version < service_version and addon_id != "script.easytv":
        log.warning("Clone addon out of date", event="clone.outdated")
        if dialog.yesno('EasyTV', lang(32110) + '\n' + lang(32111)) == 1:
            import os
            update_script = os.path.join(script_path, 'resources', 'update_clone.py')
            xbmc.executebuiltin(
                f'RunScript({update_script},{window.getProperty("EasyTV.ServicePath")},'
                f'{script_path},{addon_id},{script_name})'
            )
            return False
    return True


if __name__ == "__main__":
    addon = xbmcaddon.Addon()
    addon_version = tuple(int(x) for x in addon.getAddonInfo('version').split('.'))
    addon_id = addon.getAddonInfo('id')
    script_path = addon.getAddonInfo('path')
    script_name = addon.getAddonInfo('Name')

    log = get_logger('default')
    log.info("EasyTV addon started", event="ui.start")

    # Handle special modes from command line
    if len(sys.argv) > 1:
        _handle_special_modes(sys.argv[1], addon, log)
        sys.exit()

    window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    dialog = xbmcgui.Dialog()

    # Check service status
    if window.getProperty('EasyTV_service_running') == 'starting':
        dialog.ok("EasyTV", lang(32115) + '\n' + lang(32116))
        sys.exit()

    if not _check_service_running(window, log):
        log.warning("EasyTV service not running", event="service.missing")
        if dialog.yesno('EasyTV', lang(32106) + '\n' + lang(32107)) == 1:
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
                '"id":1,"params":{"addonid":"script.easytv","enabled":false}}'
            )
            xbmc.sleep(ADDON_RESTART_DELAY_MS)
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled",'
                '"id":1,"params":{"addonid":"script.easytv","enabled":true}}'
            )
        sys.exit()

    # Check version compatibility
    if not _handle_version_mismatch(addon_version, addon_id, script_path, script_name, window, dialog, log):
        sys.exit()

    main_entry(addon, log)
    log.info("EasyTV addon finished", event="ui.stop")
