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
EasyTV Playback Monitor.

Monitors playback events and handles episode transitions, previous episode
checks, and next episode prompts.
Extracted from service.py as part of modularization.

Logging:
    Module: playback_monitor
    Events: None (debug/info logging only, no formal events)
"""
from __future__ import annotations

import ast
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Union

import xbmc
import xbmcgui

from resources.lib.constants import (
    NOTIFICATION_DURATION_MS,
    PLAYER_STOP_DELAY_MS,
    PLAYLIST_ADD_DELAY_MS,
    PLAYLIST_START_DELAY_MS,
    MOVIE_RANDOM_SEEK_MAX_RATIO,
    MOVIE_RANDOM_SEEK_MIN_PERCENT,
    PERCENT_MULTIPLIER,
    RANDOM_PERCENT_MAX,
    RESUME_REWIND_SECONDS,
    SECONDS_TO_MS_MULTIPLIER,
)
from resources.lib.utils import (
    get_logger,
    json_query,
    lang,
    runtime_converter,
)
from resources.lib.data.queries import (
    build_add_episode_query,
    build_player_seek_query,
    get_playing_item_query,
)
from resources.lib.data.shows import (
    parse_season_episode_string,
    resolve_istream_episode,
)

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


@dataclass
class PlaybackSettings:
    """
    Settings relevant to playback monitoring.
    
    Provides a snapshot of current settings to avoid accessing globals.
    """
    previous_episode_check: bool = False
    nextprompt: bool = False
    nextprompt_in_playlist: bool = False
    playlist_notifications: bool = True
    resume_partials: bool = False
    movies_random_start: bool = False
    promptdefaultaction: int = 0
    promptduration: int = 0


# Type aliases for callbacks
# Note: Use List/Dict instead of list/dict for Python 3.8 compatibility (Kodi uses 3.8)
SettingsGetter = Callable[[], PlaybackSettings]
RandomShowsGetter = Callable[[], List[int]]
RefreshShowCallback = Callable[[List[int]], None]
ClearTargetCallback = Callable[[], None]
GetNextPromptInfoCallback = Callable[[], Dict]
SetNextPromptInfoCallback = Callable[[Dict], None]


class PlaybackMonitor(xbmc.Player):
    """
    Monitors playback events for TV episodes and movies.
    
    Handles:
    - Episode playback detection and tracking
    - Previous episode warnings
    - Resume point handling
    - Next episode prompts at end of playback
    - Movie notifications and random start positions
    
    Args:
        window: The Kodi home window for property access.
        dialog: The Kodi dialog instance for user prompts.
        get_settings: Callback to get current playback settings.
        get_random_order_shows: Callback to get random order shows list.
        on_refresh_show: Callback to refresh show episode data.
        clear_target: Callback to clear the playback target.
        get_nextprompt_info: Callback to get next prompt episode info.
        set_nextprompt_info: Callback to set next prompt episode info.
        logger: Optional logger instance.
    """
    
    # Class-level state for backward compatibility with code that accesses
    # LazyPlayer.playing_showid, LazyPlayer.playing_epid, etc.
    pending_next_episode: Union[int, bool] = False
    pl_running: str = 'null'
    playing_showid: Union[int, bool] = False
    playing_epid: Union[int, bool] = False
    nextprompt_trigger: bool = False
    nextprompt_trigger_override: bool = True
    
    def __init__(
        self,
        window: xbmcgui.Window,
        dialog: xbmcgui.Dialog,
        get_settings: SettingsGetter,
        get_random_order_shows: RandomShowsGetter,
        on_refresh_show: RefreshShowCallback,
        clear_target: ClearTargetCallback,
        get_nextprompt_info: GetNextPromptInfoCallback,
        set_nextprompt_info: SetNextPromptInfoCallback,
        logger: Optional[StructuredLogger] = None,
    ):
        """Initialize the playback monitor with callbacks."""
        super().__init__()
        
        self._window = window
        self._dialog = dialog
        self._get_settings = get_settings
        self._get_random_order_shows = get_random_order_shows
        self._on_refresh_show = on_refresh_show
        self._clear_target = clear_target
        self._get_nextprompt_info = get_nextprompt_info
        self._set_nextprompt_info = set_nextprompt_info
        self._log = logger or get_logger('playback_monitor')
        
        # Reset class-level state
        PlaybackMonitor.pending_next_episode = False
        PlaybackMonitor.pl_running = 'null'
        PlaybackMonitor.playing_showid = False
        PlaybackMonitor.playing_epid = False
        PlaybackMonitor.nextprompt_trigger = False
        PlaybackMonitor.nextprompt_trigger_override = True
        
        # Instance-level state
        self._ep_details: dict = {}
        self._pl_running_local: str = 'null'
        self._pending_movie_random_start: bool = False
    
    def onPlayBackStarted(self) -> None:
        """
        Handle playback start events.
        
        Detects what is playing (episode or movie) and:
        - Checks for previous episode warnings
        - Shows playlist notifications
        - Handles resume points
        - Sets up episode tracking
        """
        self._log.debug("Playback started")
        self._pending_movie_random_start = False  # Reset for new playback
        settings = self._get_settings()
        
        self._clear_target()
        PlaybackMonitor.nextprompt_trigger_override = True
        
        # Check what is playing
        self._ep_details = json_query(get_playing_item_query(), True)
        self._log.debug("Now playing details", details=self._ep_details)
        
        self._pl_running_local = self._window.getProperty("EasyTV.playlist_running")
        
        if 'item' not in self._ep_details or 'type' not in self._ep_details['item']:
            self._log.debug("Playback started handler complete (no item)")
            return
        
        playlist_length = xbmc.getInfoLabel('VideoPlayer.PlaylistLength')
        
        # Check if this is a playlist - suppress next_ep_notify when there are
        # more than 1 items unless it IS a EasyTV playlist and user wants prompts
        if playlist_length != '1' and not all([
            self._pl_running_local == 'true',
            settings.nextprompt_in_playlist
        ]):
            self._log.debug("Next prompt suppressed (playlist mode)")
            PlaybackMonitor.nextprompt_trigger_override = False
        
        item_type = self._ep_details['item']['type']
        
        if item_type in ['unknown', 'episode']:
            self._handle_episode_playback(settings)
        elif item_type == 'movie' and self._pl_running_local == 'true':
            self._handle_movie_playback(settings)
        
        self._log.debug("Playback started handler complete")
    
    def onAVStarted(self) -> None:
        """
        Handle audio/video stream start.
        
        This fires when the actual A/V stream begins, at which point
        video metadata like duration is available. Used for movie
        random start seeking.
        """
        if not self._pending_movie_random_start:
            return
        
        self._pending_movie_random_start = False
        self._log.debug("AV started - processing pending movie random start")
        
        time = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))
        self._log.debug("Movie duration retrieved", duration_seconds=time)
        
        if time > 0:
            # Calculate random seek point between MIN and MAX percent
            # Squared random factor biases toward earlier positions
            max_percent = int(MOVIE_RANDOM_SEEK_MAX_RATIO * PERCENT_MULTIPLIER)
            random_factor = (random.randint(0, RANDOM_PERCENT_MAX) / 100.0) ** 2
            seek_point = MOVIE_RANDOM_SEEK_MIN_PERCENT + int(
                (max_percent - MOVIE_RANDOM_SEEK_MIN_PERCENT) * random_factor
            )
            self._log.debug("Seeking to random point", seek_percent=seek_point)
            json_query(build_player_seek_query(seek_point), True)
        else:
            self._log.warning("Movie duration unavailable, skipping random start")
    
    def _handle_episode_playback(self, settings: PlaybackSettings) -> None:
        """
        Handle episode playback started.
        
        Args:
            settings: Current playback settings.
        """
        episode_np = parse_season_episode_string(self._ep_details['item']['episode'])
        season_np = parse_season_episode_string(self._ep_details['item']['season'])
        showtitle = self._ep_details['item']['showtitle']
        now_playing_show_id = int(self._ep_details['item']['tvshowid'])
        
        previous_episode_check = settings.previous_episode_check
        random_order_shows = self._get_random_order_shows()
        
        try:
            now_playing_episode_id = int(self._ep_details['item']['id'])
        except KeyError:
            if self._ep_details['item']['episode'] < 0:
                previous_episode_check = False
                now_playing_episode_id = False
                now_playing_show_id = False
            else:
                previous_episode_check, now_playing_show_id, now_playing_episode_id = resolve_istream_episode(
                    now_playing_show_id, showtitle, episode_np, season_np,
                    random_order_shows, refresh_callback=self._on_refresh_show
                )
        
        self._log.debug("Previous episode check", enabled=previous_episode_check)
        
        # Check for previous episode warning
        if (previous_episode_check and 
            now_playing_show_id not in random_order_shows and 
            self._pl_running_local != 'true'):
            self._check_previous_episode(
                now_playing_show_id, now_playing_episode_id, showtitle
            )
        
        # Show playlist notification
        if self._pl_running_local == 'true' and settings.playlist_notifications:
            xbmc.executebuiltin(
                'Notification(%s,%s S%sE%s,%i)' % (
                    lang(32163), showtitle, season_np, episode_np,
                    NOTIFICATION_DURATION_MS
                )
            )
        
        # Handle resume point
        if (self._pl_running_local == 'true' and settings.resume_partials) or \
           self._pl_running_local == 'listview':
            self._handle_resume_point()
        
        # Set up episode tracking
        PlaybackMonitor.playing_epid = now_playing_episode_id
        PlaybackMonitor.playing_showid = now_playing_show_id
        self._log.debug(
            "PlaybackMonitor detected episode",
            show_id=PlaybackMonitor.playing_showid,
            episode_id=PlaybackMonitor.playing_epid
        )
    
    def _check_previous_episode(
        self, 
        show_id: int, 
        episode_id: int, 
        showtitle: str
    ) -> None:
        """
        Check if user is playing a later episode than the stored next episode.
        
        If so, offer to play the stored (earlier) episode instead.
        
        Args:
            show_id: The TV show ID.
            episode_id: The currently playing episode ID.
            showtitle: The show title for display.
        """
        self._log.debug("Previous episode check passed, checking ondeck")
        
        try:
            ondeck_list = ast.literal_eval(
                self._window.getProperty(f"EasyTV.{show_id}.ondeck_list")
            )
            stored_epid = int(
                self._window.getProperty(f"EasyTV.{show_id}.EpisodeID")
            )
            stored_seas = parse_season_episode_string(
                int(self._window.getProperty(f"EasyTV.{show_id}.Season"))
            )
            stored_epis = parse_season_episode_string(
                int(self._window.getProperty(f"EasyTV.{show_id}.Episode"))
            )
        except (ValueError, SyntaxError):
            return
        
        if episode_id in ondeck_list[1:] and stored_epid:
            # Pause playback
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":false},"id":1}'
            )
            
            # Show notification dialog
            msg = (lang(32161) % (showtitle, stored_seas, stored_epis)) + '\n' + lang(32162)
            dialog_result = self._dialog.yesno(lang(32160), msg)
            self._log.debug("User dialog result", result=dialog_result)
            
            if dialog_result == 0:
                # User chose to continue with current episode - unpause
                xbmc.executeJSONRPC(
                    '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                    '"params":{"playerid":1,"play":true},"id":1}'
                )
            else:
                # User chose to play stored episode
                xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "Player.Stop", '
                    '"params": { "playerid": 1 }, "id": 1}'
                )
                xbmc.sleep(PLAYER_STOP_DELAY_MS)
                xbmc.executeJSONRPC(
                    '{ "jsonrpc": "2.0", "method": "Player.Open", '
                    '"params": { "item": { "episodeid": %d }, '
                    '"options":{ "resume": true }  }, "id": 1 }' % stored_epid
                )
    
    def _handle_resume_point(self) -> None:
        """Handle resuming playback from a saved position with slight rewind."""
        res_point = self._ep_details['item'].get('resume', {})
        if res_point.get('position', 0) > 0:
            # Rewind slightly to help catch context
            position = max(0, res_point['position'] - RESUME_REWIND_SECONDS)
            seek_point = int((position / float(res_point['total'])) * 100)
            self._log.debug(
                "Resuming with rewind",
                original_position=res_point['position'],
                rewound_position=position,
                seek_percent=seek_point
            )
            json_query(build_player_seek_query(seek_point), True)
    
    def _handle_movie_playback(self, settings: PlaybackSettings) -> None:
        """
        Handle movie playback in EasyTV playlist.
        
        Shows notification and handles resume/random start.
        Random start is deferred to onAVStarted when video metadata is available.
        
        Args:
            settings: Current playback settings.
        """
        if settings.playlist_notifications:
            xbmc.executebuiltin(
                'Notification(%s,%s,%i)' % (
                    lang(32163),
                    self._ep_details['item']['label'],
                    NOTIFICATION_DURATION_MS
                )
            )
        
        resume_info = self._ep_details['item'].get('resume', {})
        
        if settings.resume_partials and resume_info.get('position', 0) > 0:
            # Rewind slightly to help catch context
            position = max(0, resume_info['position'] - RESUME_REWIND_SECONDS)
            seek_point = int((position / float(resume_info['total'])) * 100)
            self._log.debug(
                "Movie resuming with rewind",
                original_position=resume_info['position'],
                rewound_position=position,
                seek_percent=seek_point
            )
            json_query(build_player_seek_query(seek_point), True)
        elif settings.movies_random_start and self._ep_details['item'].get('playcount', 0) != 0:
            # Defer random seek to onAVStarted when duration is available
            self._pending_movie_random_start = True
            self._log.debug("Movie random start pending (will seek on AV start)")
    
    def onPlayBackStopped(self) -> None:
        """Handle playback stopped events."""
        self._pending_movie_random_start = False  # Reset any pending random start
        
        nextprompt_info = self._get_nextprompt_info()
        pre_showid = nextprompt_info.get('tvshowid')
        
        if pre_showid:
            self._window.setProperty(f"EasyTV.{pre_showid}.Resume", 'true')
        
        self.onPlayBackEnded()
    
    def onPlayBackEnded(self) -> None:
        """
        Handle playback ended events.
        
        Shows next episode prompt if configured and conditions are met.
        """
        # Get info for previously played episode while still available
        nextprompt_info = self._get_nextprompt_info()
        pre_seas = nextprompt_info.get('season', None)
        pre_ep = nextprompt_info.get('episode', None)
        pre_title = nextprompt_info.get('showtitle', None)
        pre_epid = nextprompt_info.get('episodeid', None)
        
        if any([pre_seas is None, pre_ep is None, pre_title is None, pre_epid is None]):
            self._log.warning(
                "Next prompt info incomplete",
                event="playback.prompt_incomplete",
                season=pre_seas, episode=pre_ep, title=pre_title, episode_id=pre_epid
            )
            self._set_nextprompt_info({})
            return
        
        self._log.debug("Playback ended")
        
        PlaybackMonitor.playing_epid = False
        
        # Give the playlist a chance to start the next item
        xbmc.sleep(PLAYLIST_START_DELAY_MS)
        
        # Get current settings
        settings = self._get_settings()
        
        # Check if something new is playing
        now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
        
        # If nothing playing, or playlist mode with next prompt enabled
        if now_name == '' or all([
            self._pl_running_local == 'true', 
            settings.nextprompt_in_playlist
        ]):
            # Clear playlist running flag if nothing playing and was a playlist
            if now_name == '' and self._pl_running_local == 'true':
                self._window.setProperty("EasyTV.playlist_running", 'false')
            
            # Show next episode prompt if conditions are met
            if PlaybackMonitor.nextprompt_trigger and PlaybackMonitor.nextprompt_trigger_override:
                self._show_next_episode_prompt(
                    now_name, pre_seas, pre_ep, pre_title, pre_epid, settings
                )
            
            self._set_nextprompt_info({})
        
        self._log.debug("Playback ended handler complete")
    
    def _show_next_episode_prompt(
        self,
        now_name: str,
        pre_seas: int,
        pre_ep: int,
        pre_title: str,
        pre_epid: int,
        settings: PlaybackSettings,
    ) -> None:
        """
        Show the next episode prompt dialog.
        
        Args:
            now_name: Currently playing show name (empty if nothing playing).
            pre_seas: Season number of next episode.
            pre_ep: Episode number of next episode.
            pre_title: Show title.
            pre_epid: Episode ID of next episode.
            settings: Current playback settings.
        """
        paused = False
        
        if now_name != '':
            # Something is playing (EasyTV playlist with prompts enabled)
            # Pause it to show the prompt
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":false},"id":1}'
            )
            paused = True
        
        PlaybackMonitor.nextprompt_trigger = False
        
        SE = str(int(pre_seas)) + 'x' + str(int(pre_ep))
        
        self._log.debug("Prompt default action", action=settings.promptdefaultaction)
        
        # Set up button labels based on default action
        if settings.promptdefaultaction == 0:
            ylabel = lang(32092)  # "Play"
            nlabel = lang(32091)  # "Don't Play"
            prompt = -1
        elif settings.promptdefaultaction == 1:
            ylabel = lang(32091)
            nlabel = lang(32092)
            prompt = -1
        else:
            ylabel = lang(32092)
            nlabel = lang(32091)
            prompt = -1
        
        # Show dialog
        msg = (lang(32168) % (pre_title, SE)) + '\n' + lang(32162)
        heading = lang(32167) % settings.promptduration if settings.promptduration > 0 else lang(32167) % 0
        
        if settings.promptduration > 0:
            prompt = self._dialog.yesno(
                heading, msg, nolabel=nlabel, yeslabel=ylabel,
                autoclose=int(settings.promptduration * SECONDS_TO_MS_MULTIPLIER)
            )
        else:
            prompt = self._dialog.yesno(heading, msg, nolabel=nlabel, yeslabel=ylabel)
        
        self._log.debug("Prompt dialog shown", initial_result=prompt)
        
        # Interpret result based on default action setting
        if prompt == -1:
            prompt = 0
        elif prompt == 0:
            if settings.promptdefaultaction == 1:
                prompt = 1
        elif prompt == 1:
            if settings.promptdefaultaction == 1:
                prompt = 0
        
        self._log.debug("Prompt final result", result=prompt)
        
        if prompt:
            # User chose to play next episode
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0","id": 1, "method": "Playlist.Clear",'
                '"params": {"playlistid": 1}}'
            )
            json_query(build_add_episode_query(int(pre_epid)), False)
            xbmc.sleep(PLAYLIST_ADD_DELAY_MS)
            xbmc.Player().play(xbmc.PlayList(1))
            if paused:
                self._log.debug("Unpausing playback after prompt")
                xbmc.executeJSONRPC(
                    '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                    '"params":{"playerid":1,"play":true},"id":1}'
                )
        elif now_name != '' and paused:
            # User declined - unpause if we paused
            self._log.debug("Unpausing playback (user declined prompt)")
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":true},"id":1}'
            )
