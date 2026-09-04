#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#
"""
EasyTV Main UI Logic - browsing episodes and creating random playlists.

Modernized for Kodi 21+ (Nexus/Omega).

Logging:
    Module: default
    Events:
        - ui.start (INFO): Addon UI started
        - ui.stop (INFO): Addon UI finished
        - playlist.save (INFO): Playlist saved to file
        - version.mismatch (WARNING): Addon/service version mismatch
        - clone.outdated (WARNING): Clone addon needs update
        - clone.update_flag_cleared (INFO): Skipped version check after recent update
        - clone.update_flag_stale (INFO): Update flag outdated, another update occurred
        - service.missing (WARNING): EasyTV service not running
"""

import os
import sys
import time
from typing import List

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.constants import (
    ADDON_RESTART_DELAY_MS,
    KODI_HOME_WINDOW_ID,
    PROP_FORCE_SYNC,
    PROP_SERVICE_HEARTBEAT,
    PROP_SERVICE_PATH,
    PROP_SERVICE_RUNNING,
    PROP_VERSION,
    SERVICE_HEARTBEAT_MAX_AGE_S,
    SERVICE_POLL_SLEEP_MS,
    SERVICE_POLL_TIMEOUT_TICKS,
    SETTING_MULTI_INSTANCE_SYNC,
)
from resources.lib.playback.browse_mode import EpisodeListConfig, build_episode_list
from resources.lib.playback.random_player import (
    CONTENT_MOVIES_ONLY,
    RandomPlaylistConfig,
    build_random_playlist,
)
from resources.lib.ui.dialogs import show_confirm, show_playlist_selection
from resources.lib.utils import (
    compare_versions,
    get_bool_setting,
    get_int_setting,
    get_logger,
    is_clone,
    lang,
    parse_show_id_list,
    parse_version,
    restart_addon,
)


def _get_population(filter_enabled, populate_by, playlist_source,
                    user_playlist_path, selected_shows, dialog, log,
                    addon_name='EasyTV'):
    """Build population filter based on settings."""
    if not filter_enabled:
        return {'none': ''}
    if populate_by == '1':
        if playlist_source == '0':
            # Ask each time - pass tvshows filter for TV show playlists
            return {'playlist': show_playlist_selection(
                dialog=dialog, logger=log, playlist_type='tvshows'
            )}
        # Use default playlist - check file exists first
        if user_playlist_path and user_playlist_path != 'none':
            if not xbmcvfs.exists(user_playlist_path):
                log.warning("TV show playlist file not found",
                           event="playlist.missing", path=user_playlist_path)
                # 32607 = "TV show playlist not found. Please update your settings."
                dialog.ok(addon_name, lang(32607))
                sys.exit()
            return {'playlist': user_playlist_path}
        return {'none': ''}
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


def _signal_force_sync_on_open(window):
    """Signal the service to run an immediate shared-DB sync (on-open trigger).

    Set on UI launch so a consuming instance reflects cross-instance changes
    right away instead of waiting for the next periodic tick. No-op when
    multi-instance sync is disabled. The daemon clears the flag within one
    event-loop tick.
    """
    if get_bool_setting(SETTING_MULTI_INSTANCE_SYNC):
        window.setProperty(PROP_FORCE_SYNC, '1')


def _read_selected_shows(addon) -> List[int]:
    """Return the show-filter selection for this addon instance.

    Clones read their own 'selection' setting; the main addon reads the
    EasyTV.selection window property (written by the service).
    Empty or invalid input yields [] (no shows).
    """
    if is_clone(addon):
        return parse_show_id_list(addon.getSetting('selection'))
    try:
        raw = xbmcgui.Window(KODI_HOME_WINDOW_ID).getProperty("EasyTV.selection")
        return parse_show_id_list(raw)
    except (ValueError, SyntaxError):
        return []


def _read_random_order_shows(addon) -> List[int]:
    """Return the random-order show list for this addon instance.

    Clones read their own 'random_order_shows' setting; the main addon
    reads the EasyTV.random_order_shows window property (written by the
    service). Empty or invalid input yields [] (no shows).
    """
    if is_clone(addon):
        return parse_show_id_list(addon.getSetting('random_order_shows'))
    try:
        raw = xbmcgui.Window(KODI_HOME_WINDOW_ID).getProperty("EasyTV.random_order_shows")
        return parse_show_id_list(raw)
    except (ValueError, SyntaxError):
        return []


def main_entry(addon, log):
    """Main entry point - determines mode and launches appropriate functionality."""
    log.debug("Main entry point")

    dialog = xbmcgui.Dialog()
    window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
    script_path = addon.getAddonInfo('path')
    addon_name = addon.getAddonInfo('name')

    # Track which addon (main or clone) started playback for service dialogs
    window.setProperty('EasyTV.SourceAddonId', addon.getAddonInfo('id'))

    # On-open trigger: ask the service to sync now so cross-instance changes
    # appear immediately instead of waiting for the next periodic tick.
    _signal_force_sync_on_open(window)

    # The art-cache session flag is deliberately NOT cleared here. Clearing it
    # made the ~1.2s art query run on every launch instead of once per Kodi
    # session, which was ~38% of a 3.2s median launch measured across 268
    # launches. The stale latch it guarded against cannot occur: _fetch_show_art
    # only latches when at least one show actually had a poster (issue #2), and
    # library_monitor clears the flag when a video scan finishes, which is the
    # only way cached art goes out of date.

    # Load settings
    primary_function = addon.getSetting('primary_function')
    filter_enabled = get_bool_setting('filter_enabled')
    sort_by = get_int_setting('sort_by')
    sort_reverse = get_bool_setting('sort_reverse')

    selected_shows = _read_selected_shows(addon)

    random_order_shows = _read_random_order_shows(addon)

    population = _get_population(
        filter_enabled, addon.getSetting('populate_by'),
        addon.getSetting('playlist_source'), addon.getSetting('user_playlist_path'),
        selected_shows, dialog, log, addon_name=addon_name
    )

    # Determine mode: 0=browse, 1=random playlist, 2=ask
    if primary_function == '2':
        choice = show_confirm(addon_name, lang(32100) + '\n\n' + lang(32101),
                              yes_label=lang(32103), no_label=lang(32102))
        # show_confirm returns bool: True=yes("Start playlist"), False=no("Show me")
    else:
        choice = int(primary_function) if primary_function in ('0', '1') else 0

    language = xbmc.getInfoLabel('System.Language')

    # playlist_content is read here (rather than inside the choice == 1
    # branch below) so the guided flow's movies-only guard and the branch
    # itself share a single read. The 0 (TV-only) default is inert when
    # choice != 1, since nothing reads it outside the playlist branch.
    playlist_content = get_int_setting('playlist_content') if choice == 1 else 0

    allowed_show_ids = None
    if get_bool_setting('guided_enabled'):
        if choice == 1 and playlist_content == CONTENT_MOVIES_ONLY:
            # Movies-only playlists have no TV shows to narrow.
            log.debug("Guided flow skipped for movies-only playlist",
                      event="wizard.not_applicable")
        else:
            from resources.lib.ui.wizard import run_wizard
            wizard_result = run_wizard(
                addon_id=addon.getAddonInfo('id'),
                population=population, mode_choice=choice, logger=log)
            if wizard_result is None:
                sys.exit()
            allowed_show_ids = wizard_result.allowed_show_ids

    if choice == 1:
        # Random playlist mode
        # Get movie playlist setting if movies are included
        movie_playlist = None
        # playlist_content: 0=TV only, 1=mixed, 2=movies only
        if playlist_content != 0:  # Not TV-only mode
            movie_playlist_path = addon.getSetting('movie_user_playlist_path')
            if movie_playlist_path and movie_playlist_path not in ('none', 'empty', ''):
                # Check file exists
                if not xbmcvfs.exists(movie_playlist_path):
                    log.warning("Movie playlist file not found",
                               event="playlist.missing", path=movie_playlist_path)
                    # 32606 = "Movie playlist not found. Please update your settings."
                    dialog.ok(addon_name, lang(32606))
                    sys.exit()
                movie_playlist = movie_playlist_path

        build_random_playlist(
            population=population,
            random_order_shows=random_order_shows,
            config=RandomPlaylistConfig(
                length=get_int_setting('length'),
                playlist_content=playlist_content,
                episode_selection=get_int_setting('episode_selection'),
                movie_selection=get_int_setting('movie_selection'),
                movie_chance=get_int_setting('movie_chance'),
                start_partials_tv=get_bool_setting('start_partials_tv'),
                start_partials_movies=get_bool_setting('start_partials_movies'),
                premieres=get_int_setting('premieres'),
                season_premieres=get_int_setting('season_premieres'),
                multiple_shows=get_bool_setting('multiple_shows'),
                multiple_shows_uniform=get_int_setting('multiple_shows_uniform') == 1,
                sort_by=sort_by, sort_reverse=sort_reverse, language=language,
                movie_playlist=movie_playlist,
                unwatched_ratio=get_int_setting('unwatched_ratio'),
                duration_filter_enabled=(get_bool_setting('duration_filter_enabled')
                                         if allowed_show_ids is None else False),
                duration_min=get_int_setting('duration_min'),
                duration_max=get_int_setting('duration_max'),
                allowed_show_ids=allowed_show_ids,
            ),
            logger=log,
            addon_id=addon.getAddonInfo('id'),
            clone_mode=is_clone(addon),
        )
    else:
        # Browse mode - data fetching and filtering handled internally by build_episode_list
        build_episode_list(
            population=population,
            random_order_shows=random_order_shows,
            config=EpisodeListConfig(
                skin=_get_skin_setting(addon),
                limit_shows=get_bool_setting('limit_shows'),
                window_length=get_int_setting('window_length'),
                skin_return=get_bool_setting('skin_return'),
                excl_random_order_shows=get_bool_setting('excl_random_order_shows'),
                script_path=script_path,
                duration_filter_enabled=(get_bool_setting('duration_filter_enabled')
                                         if allowed_show_ids is None else False),
                duration_min=get_int_setting('duration_min'),
                duration_max=get_int_setting('duration_max'),
                sort_by=sort_by,
                sort_reverse=sort_reverse,
                language=language,
                series_premieres=get_int_setting('premieres'),
                season_premieres=get_int_setting('season_premieres'),
                clone_mode=is_clone(addon),
                allowed_show_ids=allowed_show_ids,
            ),
            monitor=xbmc.Monitor(),
            logger=log
        )


def _handle_special_modes(mode, addon, log, addon_name='EasyTV'):
    """Handle special invocation modes (from settings actions)."""
    if mode == 'playlist':
        # Parse optional playlist type from argv[2]
        playlist_type = sys.argv[2] if len(sys.argv) > 2 else None
        log.debug("Playlist selection mode", playlist_type=playlist_type)
        from resources import playlists
        playlists.Main(playlist_type)

        # Force-close any lingering dialog instances to prevent stale cache
        # Then reopen settings as a fresh instance after a short delay
        # Note: Using 00:01 (MM:SS) format for AlarmClock compatibility
        # Use addon's own ID so clones reopen their own settings, not main addon's
        addon_id = addon.getAddonInfo('id')
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            f'AlarmClock(EasyTVSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
        )

    elif mode == 'selector':
        log.debug("Selector mode")
        from resources import selector
        selector.Main()

        # Force-close any lingering dialog instances to prevent stale cache
        # Then reopen settings as a fresh instance after a short delay
        # Note: Using 00:01 (MM:SS) format for AlarmClock compatibility
        # Use addon's own ID so clones reopen their own settings, not main addon's
        addon_id = addon.getAddonInfo('id')
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            f'AlarmClock(EasyTVSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
        )

    elif mode == 'clone':
        log.debug("Clone creation mode")
        from resources import clone
        clone.Main()

    elif mode == 'exporter':
        log.debug("Exporter mode")
        from resources import episode_exporter
        episode_exporter.Main()

    elif mode == 'set_icon':
        log.debug("Set custom icon mode")
        from resources.lib.utils import invalidate_icon_cache, set_custom_icon
        addon_id = addon.getAddonInfo('id')
        if set_custom_icon(addon_id):
            invalidate_icon_cache(addon_id)
            xbmc.executebuiltin(
                'Notification(%s,%s,%i,%s)' % (
                    addon_name, lang(32740), 3000,
                    os.path.join(addon.getAddonInfo('path'), 'icon.png')
                )
            )
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            f'AlarmClock(EasyTVSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
        )

    elif mode == 'reset_icon':
        log.debug("Reset icon mode")
        from resources.lib.utils import invalidate_icon_cache, reset_icon
        addon_id = addon.getAddonInfo('id')
        if reset_icon(addon_id):
            invalidate_icon_cache(addon_id)
            xbmc.executebuiltin(
                'Notification(%s,%s,%i,%s)' % (
                    addon_name, lang(32741), 3000,
                    os.path.join(addon.getAddonInfo('path'), 'icon.png')
                )
            )
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            f'AlarmClock(EasyTVSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
        )

    elif mode == 'clear_sync_data':
        log.debug("Clear sync data mode")
        from resources import clear_sync_data
        clear_sync_data.main()

    elif mode == 'guided_genres':
        log.debug("Guided genre preset picker mode")
        from resources import genre_selector
        genre_selector.Main()

        addon_id = addon.getAddonInfo('id')
        xbmc.executebuiltin('Dialog.Close(all,true)')
        xbmc.executebuiltin(
            f'AlarmClock(EasyTVSettings,Addon.OpenSettings({addon_id}),00:01,silent)'
        )

    elif mode == 'dialog_preview':
        log.debug("Dialog preview mode")
        try:
            from resources import dialog_preview
            override = sys.argv[2] if len(sys.argv) > 2 else None
            dialog_preview.Main(override)
        except Exception:
            import traceback
            xbmc.log("[EasyTV] dialog_preview error: %s" % traceback.format_exc(), xbmc.LOGERROR)
            raise


def _heartbeat_is_fresh(window) -> bool:
    """Whether the service published a timestamp recently enough to trust.

    Anything unparseable, missing, older than the limit, or dated in the future
    (a backwards clock correction) is treated as not fresh, which costs only
    the handshake below.
    """
    raw = window.getProperty(PROP_SERVICE_HEARTBEAT)
    if not raw:
        return False
    try:
        age = time.time() - float(raw)
    except (TypeError, ValueError):
        return False
    return 0 <= age <= SERVICE_HEARTBEAT_MAX_AGE_S


def _check_service_running(window):
    """Check if EasyTV service is running. Returns True if running.

    A recent service heartbeat proves liveness outright. The service can only
    answer the marco/polo handshake between operations, so a launch landing
    inside a long blocking query used to wait for it to finish (measured at
    2.88s, with a 5s timeout beyond which the user is ejected with a restart
    prompt).

    Falling back rather than failing is deliberate: a stale heartbeat means the
    service is busy or older than this UI, not that it is gone, so the original
    handshake still decides. This can therefore only make the check faster, and
    a genuinely dead service is still reported exactly as before.
    """
    if _heartbeat_is_fresh(window):
        return True

    window.setProperty(PROP_SERVICE_RUNNING, 'marco')
    count = 0
    while window.getProperty(PROP_SERVICE_RUNNING) == 'marco':
        count += 1
        if count > SERVICE_POLL_TIMEOUT_TICKS:
            return False
        xbmc.sleep(SERVICE_POLL_SLEEP_MS)
    return True


def _handle_version_mismatch(addon_version, addon_version_str, addon_id, script_path, script_name, window, dialog, log):
    """Check version compatibility. Returns True if OK to proceed."""
    try:
        service_version_str = window.getProperty(PROP_VERSION)
        if not service_version_str:
            service_version = (0, 0, 0, 0, 0)
            service_version_str = "0.0.0"
        else:
            service_version = parse_version(service_version_str)
    except (ValueError, SyntaxError):
        service_version = (0, 0, 0, 0, 0)
        service_version_str = "0.0.0"

    if addon_version != service_version and addon_id == "script.easytv":
        log.warning("Version mismatch", event="version.mismatch",
                    addon_version=addon_version_str, service_version=service_version_str)
        dialog.ok(script_name, lang(32108))
        return False

    # Check if clone is older than service (compare_versions returns -1 if v1 < v2)
    if compare_versions(addon_version_str, service_version_str) < 0 and addon_id != "script.easytv":
        # Check if we just completed an update - Kodi's addon cache may still report old version
        # Flag contains the target version we updated to, so we can detect if another update
        # happened after the flag was set (service moved past the flagged version)
        update_flag = f'EasyTV.UpdateComplete.{addon_id}'
        update_flag_version = window.getProperty(update_flag)
        if update_flag_version:
            if update_flag_version == service_version_str:
                # Don't clear the flag — Kodi's addon cache may still be stale.
                # Window properties clear naturally on Kodi restart, at which
                # point the cache is also refreshed.
                log.info("Clone update flag detected, skipping version check",
                         event="clone.update_flag_cleared", addon_id=addon_id,
                         flag_version=update_flag_version)
                return True
            else:
                # Flag is for an older version — another update happened.
                window.clearProperty(update_flag)
                log.info("Clone update flag outdated, proceeding with version check",
                         event="clone.update_flag_stale", addon_id=addon_id,
                         flag_version=update_flag_version, service_version=service_version_str)

        log.warning("Clone addon out of date", event="clone.outdated",
                    clone_version=addon_version_str, service_version=service_version_str)
        message = lang(32110) + '\n' + lang(32111) + '\n\n' + lang(32153)
        if show_confirm(script_name, message,
                        yes_label=lang(32109), no_label=lang(32734)):
            # Use main addon's update_clone.py, not the clone's old version
            # This ensures clones get the latest update logic (e.g., fixed settings replacement)
            service_path = window.getProperty(PROP_SERVICE_PATH)
            update_script = os.path.join(service_path, 'resources', 'update_clone.py')
            xbmc.executebuiltin(
                f'RunScript({update_script},{service_path},'
                f'{script_path},{addon_id},{script_name})'
            )
        return False
    return True


def main() -> None:
    """UI entry point — called from default.py."""
    try:
        addon = xbmcaddon.Addon()
        addon_version_str = addon.getAddonInfo('version')
        addon_version = parse_version(addon_version_str)
        addon_id = addon.getAddonInfo('id')
        script_path = addon.getAddonInfo('path')
        script_name = addon.getAddonInfo('Name')

        log = get_logger('default')
        log.info("EasyTV addon started", event="ui.start", addon_id=addon_id, version=addon_version_str)

        # Handle special modes from command line
        if len(sys.argv) > 1:
            _handle_special_modes(sys.argv[1], addon, log, addon_name=script_name)
            sys.exit()

        window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
        dialog = xbmcgui.Dialog()

        # Check service status
        if window.getProperty(PROP_SERVICE_RUNNING) == 'starting':
            dialog.ok(script_name, lang(32115) + '\n' + lang(32116))
            sys.exit()

        if not _check_service_running(window):
            log.warning("EasyTV service not running", event="service.missing")
            if show_confirm(script_name, lang(32106) + '\n' + lang(32107)):
                restart_addon("script.easytv", ADDON_RESTART_DELAY_MS)
            sys.exit()

        # Check version compatibility
        if not _handle_version_mismatch(addon_version, addon_version_str, addon_id, script_path, script_name, window, dialog, log):
            sys.exit()

        main_entry(addon, log)
        log.info("EasyTV addon finished", event="ui.stop")
    except SystemExit:
        pass  # Normal exit via sys.exit()
    except Exception:
        try:
            log = get_logger('default')
            log.exception("Unhandled error in EasyTV", event="ui.crash")
        except Exception:
            import traceback
            xbmc.log(f"[EasyTV] Unhandled error: {traceback.format_exc()}", xbmc.LOGERROR)
