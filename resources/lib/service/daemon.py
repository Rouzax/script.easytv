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
EasyTV Service Daemon.

Main service controller that orchestrates all service components:
- EpisodeTracker: Manages episode state in window properties
- LibraryMonitor: Handles Kodi library and settings changes
- PlaybackMonitor: Tracks playback events and prompts
- Settings: Loads and applies addon configuration

The daemon runs continuously in the background, processing events
and maintaining the episode tracking state until Kodi shuts down.

Extracted from service.py as part of modularization.

Logging:
    Logger: 'daemon' (passed from service.py) or 'service' (fallback)
    Key events:
        - service.init (INFO): Daemon initialization started
        - service.library_ready (INFO): Initial library scan complete
        - service.library_empty (INFO): No shows found after retries
        - service.loop_start (INFO): Main loop started
        - service.loop_stop (INFO): Main loop ended
        - settings.threshold (INFO): Watched threshold configured
        - settings.load (INFO): Settings loaded
        - playback.fallback (WARNING): Episode not found in expected list
        - next.pick (DEBUG): Next episode selected
        - library.refresh (DEBUG): Show episodes refreshed
    
    Timing events (DEBUG):
        - bulk_refresh: Startup/rescan with all shows
            Phases: show_query_ms, episode_query_ms, processing_ms,
                    duration_compare_ms, duration_calc_ms, duration_save_ms, playlists_ms
            Example: bulk_refresh completed | duration_ms=2500, show_count=277,
                     show_query_ms=50, episode_query_ms=1900, processing_ms=400,
                     duration_compare_ms=10, duration_calc_ms=100, duration_save_ms=10, playlists_ms=30
            Note: duration_calc_ms is low when most shows are cached; higher on first run.
        - show_refresh: Single show refresh (playback tracking)
            Phases: show_query_ms, episode_query_ms, processing_ms
            Example: show_refresh completed | duration_ms=45, show_count=1,
                     show_query_ms=10, episode_query_ms=20, processing_ms=15
    
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import ast
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    DAEMON_LOOP_SLEEP_MS,
    NOTIFICATION_DURATION_MS,
    TARGET_DETECTION_SLEEP_MS,
    TARGET_DETECTION_MAX_TICKS,
    POSITION_CHECK_INTERVAL_TICKS,
    FIRST_REGULAR_SEASON,
    EPISODE_INITIAL_VALUE,
    INITIAL_LOOP_LIMIT,
    # Database startup timing
    DB_STARTUP_CHECK_INTERVAL_MS,
    DB_STARTUP_MAX_RETRIES,
    # Smart playlist constants
    PLAYLIST_ALL_SHOWS,
    PLAYLIST_CONTINUE_WATCHING,
    PLAYLIST_START_FRESH,
    PLAYLIST_SHOW_PREMIERES,
    PLAYLIST_SEASON_PREMIERES,
    PLAYLIST_NAME_ALL_SHOWS,
    PLAYLIST_NAME_CONTINUE_WATCHING,
    PLAYLIST_NAME_START_FRESH,
    PLAYLIST_NAME_SHOW_PREMIERES,
    PLAYLIST_NAME_SEASON_PREMIERES,
    PLAYLIST_FORMAT_VERSION,
    CATEGORY_START_FRESH,
    CATEGORY_SHOW_PREMIERE,
    CATEGORY_SEASON_PREMIERE,
    # Playlist continuation
    PROP_PLAYLIST_CONFIG,
    PROP_PLAYLIST_REGENERATE,
)
from resources.lib.utils import (
    get_logger,
    get_playcount_minimum_percent,
    get_ignore_seconds_at_start,
    get_ignore_percent_at_end,
    get_bool_setting,
    json_query,
    lang,
    log_timing,
    runtime_converter,
    service_heartbeat,
)
from resources.lib.data.queries import (
    get_unwatched_shows_query,
    get_shows_by_lastplayed_query,
    build_show_episodes_query,
    build_all_episodes_no_streamdetails_query,
    build_show_episodes_with_streamdetails_query,
    build_episode_prompt_info_query,
)
from resources.lib.data.shows import (
    get_show_category,
    get_premiere_category,
    fetch_show_episode_data,
)
from resources.lib.data.smart_playlists import (
    remove_show_from_all_playlists,
    update_show_in_playlists,
    start_playlist_batch,
    flush_playlist_batch,
    load_playlist_format_version,
    save_playlist_format_version,
    delete_easytv_playlists,
)
from resources.lib.data.duration_cache import (
    load_duration_cache,
    save_duration_cache,
    calculate_median_duration,
    get_shows_needing_calculation,
    build_updated_cache,
)
from resources.lib.service.settings import load_settings, ServiceSettings
from resources.lib.service.library_monitor import LibraryMonitor
from resources.lib.service.playback_monitor import PlaybackMonitor, PlaybackSettings
from resources.lib.service.episode_tracker import EpisodeTracker, PROP_DURATION

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


# =============================================================================
# Service State Container
# =============================================================================

@dataclass
class ServiceState:
    """
    Container for service-level state.
    
    Groups all state that needs to be shared between daemon methods
    and passed to callbacks. Previously stored as class attributes on Main.
    """
    # Playback target threshold for "swap over" (percentage of runtime)
    target: Union[float, bool] = False
    
    # Info dict for next episode prompt
    nextprompt_info: dict = field(default_factory=dict)
    
    # Flag set by LibraryMonitor when database updates
    on_lib_update: bool = False
    
    # Flag for monitor override (external watch marking)
    monitor_override: bool = False
    
    # List of show IDs with available next episodes
    shows_with_next_episodes: list[int] = field(default_factory=list)


# =============================================================================
# Service Daemon Class
# =============================================================================

class ServiceDaemon:
    """
    Main service controller that manages background episode tracking.
    
    Orchestrates the interaction between:
    - EpisodeTracker: Caches episode data in window properties
    - LibraryMonitor: Responds to database and settings changes
    - PlaybackMonitor: Handles playback events and prompts
    
    The daemon maintains a list of TV shows with available next episodes
    and updates this list as playback progresses and library changes occur.
    
    Args:
        addon: The addon instance for settings access.
        logger: Optional logger instance.
    """
    
    def __init__(
        self,
        addon: Optional[xbmcaddon.Addon] = None,
        logger: Optional[StructuredLogger] = None,
    ):
        """Initialize the service daemon."""
        # Get addon if not provided
        if addon is None:
            addon = xbmcaddon.Addon()
        self._addon = addon
        
        # Initialize logger (logging system already configured by service.py)
        self._log = logger or get_logger('daemon')
        self._log.info("Service daemon initializing", event="service.init")
        
        # Get Kodi window and dialog
        self._window = xbmcgui.Window(KODI_HOME_WINDOW_ID)
        self._dialog = xbmcgui.Dialog()
        
        # Initialize state
        self._state = ServiceState()
        self._settings = ServiceSettings()
        self._position_check_count = 0
        self._initial_limit = INITIAL_LOOP_LIMIT
        
        # Instance state for playback tracking
        self._current_show_id: Union[int, bool] = False
        self._pending_next_episode: Union[int, bool] = False
        self._eject: bool = False
        self._is_random_show: bool = False
        
        # Cache playback completion threshold from Kodi settings
        self._playback_complete_threshold = get_playcount_minimum_percent() / 100.0
        self._log.info(
            "Watched threshold configured",
            event="settings.threshold",
            percent=int(self._playback_complete_threshold * 100)
        )
        
        # Log Kodi's resume point settings (from advancedsettings.xml)
        self._log.info(
            "Resume point thresholds configured",
            event="settings.resume_threshold",
            ignore_seconds_at_start=get_ignore_seconds_at_start(),
            ignore_percent_at_end=get_ignore_percent_at_end()
        )
        
        # Set initial window properties
        version_tuple = tuple(int(x) for x in self._addon.getAddonInfo('version').split('.'))
        self._window.setProperty("EasyTV.Version", str(version_tuple))
        self._window.setProperty("EasyTV.ServicePath", str(self._addon.getAddonInfo('path')))
        self._window.setProperty('EasyTV_service_running', 'starting')
        
        # Create components (done in initialize())
        self._player: Optional[PlaybackMonitor] = None
        self._monitor: Optional[LibraryMonitor] = None
        self._episode_tracker: Optional[EpisodeTracker] = None
        
        # All show IDs in library
        self._all_shows_list: list[int] = []
    
    def initialize(self) -> None:
        """
        Initialize service components.
        
        Creates the PlaybackMonitor, LibraryMonitor, and EpisodeTracker,
        then performs initial library scan to populate episode data.
        """
        self._log.debug("Initializing service components")
        
        # Create PlaybackMonitor with callbacks
        self._player = PlaybackMonitor(
            window=self._window,
            dialog=self._dialog,
            get_settings=self._get_playback_settings,
            get_random_order_shows=lambda: self._settings.random_order_shows,
            on_refresh_show=self.refresh_show_episodes,
            clear_target=lambda: setattr(self._state, 'target', False),
            get_nextprompt_info=lambda: self._state.nextprompt_info,
            set_nextprompt_info=lambda info: setattr(self._state, 'nextprompt_info', info),
            logger=self._log,
        )
        
        # Create LibraryMonitor with callbacks
        self._monitor = LibraryMonitor(
            window=self._window,
            on_settings_changed=self._on_settings_changed,
            on_library_updated=lambda: setattr(self._state, 'on_lib_update', True),
            get_random_order_shows=lambda: self._settings.random_order_shows,
            on_refresh_show=self.refresh_show_episodes,
            set_player_episode_id=lambda epid: setattr(self._player, '_playing_epid', epid),
            set_player_show_id=lambda showid: setattr(self._player, '_playing_showid', showid),
            get_player_episode_id=lambda: self._player._playing_epid,
            set_monitor_override=lambda val: setattr(self._state, 'monitor_override', val),
            logger=self._log,
        )
        
        # Create EpisodeTracker for managing episode state
        self._episode_tracker = EpisodeTracker(
            window=self._window,
            on_update_smartplaylist=self._update_smartplaylist,
            logger=self._log,
        )
        
        # Initialize playlist running property
        self._window.setProperty("EasyTV.playlist_running", '')
        
        # Perform initial library scan with retry logic
        self._initial_library_scan()
        
        self._log.debug("Service components initialized")
    
    def run(self) -> None:
        """
        Main service loop.
        
        Runs continuously until Kodi shuts down, calling _process_events()
        at regular intervals to handle state changes.
        
        Lifecycle:
            1. Sets 'EasyTV_service_running' property to 'true'
            2. Optionally shows startup notification (if enabled)
            3. Enters main loop processing events every DAEMON_LOOP_SLEEP_MS
            
        Exit Conditions:
            - Kodi abort requested (shutdown/restart)
            - 'EasyTV_service_running' property cleared
        """
        self._window.setProperty('EasyTV_service_running', 'true')
        
        # Show startup notification if enabled
        if self._settings.startup:
            xbmc.executebuiltin(
                'Notification(%s,%s,%i)' % ('EasyTV', lang(32173), NOTIFICATION_DURATION_MS)
            )
        
        self._log.info("Daemon loop started", event="service.loop_start")
        
        # Main loop
        while (not self._monitor.abortRequested() and 
               self._window.getProperty('EasyTV_service_running')):
            xbmc.sleep(DAEMON_LOOP_SLEEP_MS)
            self._process_events()
        
        self._log.info("Daemon loop ended", event="service.loop_stop")
    
    def _process_events(self) -> None:
        """
        Process pending events and manage episode tracking state.
        
        Called every DAEMON_LOOP_SLEEP_MS (~100ms) to handle:
        
        1. Liveness Check: Responds to 'marco' with 'polo' for addon heartbeat
        
        2. Library Update: When LibraryMonitor detects database changes,
           refreshes the episode list for all shows
           
        3. Random Shuffle: When addon requests shuffle via window property,
           reshuffles episodes for all random-order shows
           
        4. Episode Detection: When PlaybackMonitor reports a playing episode:
           - For random shows: picks next random episode from combined deck
           - For sequential shows: advances to next episode in order
           - Stores next episode info in 'temp' window properties
           
        5. Playback Progress: Every POSITION_CHECK_INTERVAL_TICKS cycles,
           checks if playback has passed the completion threshold:
           - If passed: swaps 'temp' data to the show's actual properties
           - Sets nextprompt_trigger for end-of-episode prompt
           - Removes show from list if no more episodes
        """
        service_heartbeat()
        
        self._pending_next_episode = False
        
        # Handle library updates
        if self._state.on_lib_update:
            self._state.on_lib_update = False
            self._retrieve_all_show_ids()
            self.refresh_show_episodes(showids=self._all_shows_list, bulk=True)
        
        # Handle random order shuffle request
        shuffle_request = self._window.getProperty("EasyTV.random_order_shuffle")
        if shuffle_request == 'true':
            self._window.setProperty("EasyTV.random_order_shuffle", 'false')
            self._log.debug("Reshuffling random order shows")
            self._reshuffle_random_order_shows()
        
        # Handle playlist regeneration request (from continuation prompt)
        regen_request = self._window.getProperty(PROP_PLAYLIST_REGENERATE)
        if regen_request == 'true':
            self._window.setProperty(PROP_PLAYLIST_REGENERATE, 'false')
            self._regenerate_playlist()
        
        # Process episode playback if a tracked show is playing
        if (self._player._playing_showid and 
            self._player._playing_showid in self._state.shows_with_next_episodes):
            self._process_episode_playback()
        
        # Check playback position for swap over
        if self._state.target:
            self._check_playback_position()
        
        # Reset per-cycle state
        self._player._playing_showid = False
        self._state.monitor_override = False
        self._is_random_show = False
    
    def _process_episode_playback(self) -> None:
        """
        Process episode playback detection.
        
        When PlaybackMonitor detects an episode is playing, this method:
        - Retrieves the current ondeck/offdeck lists
        - Determines the next episode (random or sequential)
        - Caches the next episode data in 'temp' properties
        - Sets up the target time for swap over
        """
        self._log.debug(
            "Episode playback detected",
            show_id=self._player._playing_showid
        )
        
        self._current_show_id = self._player._playing_showid
        
        # Retrieve ondeck and offdeck lists from window properties
        retrieved_ondeck_string = self._window.getProperty(
            f"EasyTV.{self._current_show_id}.ondeck_list"
        )
        retrieved_offdeck_string = self._window.getProperty(
            f"EasyTV.{self._current_show_id}.offdeck_list"
        )
        
        try:
            ondeck_list = ast.literal_eval(retrieved_ondeck_string)
        except (ValueError, SyntaxError):
            ondeck_list = []
        
        try:
            offdeck_list = ast.literal_eval(retrieved_offdeck_string)
        except (ValueError, SyntaxError):
            offdeck_list = []
        
        # Get episode counts, adjusting for the currently playing episode
        temp_watched_count = int(
            self._window.getProperty(f"EasyTV.{self._current_show_id}.CountWatchedEps")
            .replace("''", '0') or '0'
        ) + 1
        temp_unwatched_count = max(0, int(
            self._window.getProperty(f"EasyTV.{self._current_show_id}.CountUnwatchedEps")
            .replace("''", '0') or '0'
        ) - 1)
        
        self._log.debug("On-deck list retrieved", ondeck=retrieved_ondeck_string)
        
        if self._current_show_id in self._settings.random_order_shows:
            self._process_random_show_episode(
                ondeck_list, offdeck_list, temp_watched_count, temp_unwatched_count
            )
        else:
            self._process_sequential_show_episode(
                ondeck_list, offdeck_list, temp_watched_count, temp_unwatched_count
            )
        
        if self._pending_next_episode:
            self._log.debug("Next episode queued", episode_id=self._pending_next_episode)
        
        # Set up next prompt info if needed
        self._prepare_next_prompt_info()
        
        # Set the target time for swap over
        self._set_playback_target()
        
        # Reset player state so this section doesn't run again
        self._player._playing_showid = False
    
    def _process_random_show_episode(
        self,
        ondeck_list: list[int],
        offdeck_list: list[int],
        watched_count: int,
        unwatched_count: int,
    ) -> None:
        """
        Process playback for a random-order show.
        
        For random shows, both ondeck and offdeck episodes are combined
        into a single pool that gets shuffled.
        
        Args:
            ondeck_list: Episodes after current position.
            offdeck_list: Skipped episodes before current position.
            watched_count: Updated watched episode count.
            unwatched_count: Updated unwatched episode count.
        """
        combined_episode_list = offdeck_list + ondeck_list
        
        if not combined_episode_list:
            self._player._playing_epid = False
            self._player._playing_showid = False
            return
        
        if self._player._playing_epid not in combined_episode_list:
            self._log.warning(
                "Playing episode not in tracked list (random show)",
                event="playback.fallback",
                show_id=self._current_show_id,
                episode_id=self._player._playing_epid
            )
            self._pending_next_episode = False
            self._player._playing_epid = False
            self._player._playing_showid = False
            return
        
        self._log.debug("Random show episode found in ondeck")
        
        # Remove currently playing episode from the appropriate list
        if self._player._playing_epid in ondeck_list:
            ondeck_list.remove(self._player._playing_epid)
        else:
            offdeck_list.remove(self._player._playing_epid)
        
        # Shuffle remaining episodes and pick next
        combined_episode_list = offdeck_list + ondeck_list
        random.shuffle(combined_episode_list)
        self._pending_next_episode = combined_episode_list[0]
        
        self._is_random_show = True
        
        # Cache next episode in temp properties
        self._episode_tracker.cache_next_episode(
            self._pending_next_episode, 'temp',
            ondeck_list, offdeck_list,
            unwatched_count, watched_count,
            is_skipped=False
        )
        
        self._player._playing_epid = False
        self._player._playing_showid = False
        
        # Handle monitor override (external watch marking)
        if self._state.monitor_override:
            self._log.debug("Monitor override: triggering swap (random show)")
            self._state.monitor_override = False
            self._player._playing_epid = False
            self._state.target = False
            self._pending_next_episode = False
            self._episode_tracker.transition_to_next_episode(self._current_show_id)
    
    def _process_sequential_show_episode(
        self,
        ondeck_list: list[int],
        offdeck_list: list[int],
        watched_count: int,
        unwatched_count: int,
    ) -> None:
        """
        Process playback for a sequential-order show.
        
        For sequential shows, only ondeck episodes are considered.
        The next episode is always the one immediately following
        the currently playing episode.
        
        Args:
            ondeck_list: Episodes after current position.
            offdeck_list: Skipped episodes (stored but not used).
            watched_count: Updated watched episode count.
            unwatched_count: Updated unwatched episode count.
        """
        combined_episode_list = ondeck_list
        
        if not combined_episode_list:
            return
        
        if self._player._playing_epid not in combined_episode_list:
            self._log.warning(
                "Playing episode not in ondeck list",
                event="playback.fallback",
                show_id=self._current_show_id,
                episode_id=self._player._playing_epid
            )
            self._pending_next_episode = False
            self._player._playing_showid = False
            self._player._playing_epid = False
            return
        
        episode_index = combined_episode_list.index(self._player._playing_epid)
        self._log.debug("Episode found in ondeck list", position=episode_index)
        
        if episode_index != len(combined_episode_list) - 1:
            # Not the last episode - queue the next one
            self._pending_next_episode = combined_episode_list[episode_index + 1]
            new_ondeck = [int(x) for x in combined_episode_list[episode_index + 1:]]
            
            # Cache next episode in temp properties
            self._episode_tracker.cache_next_episode(
                self._pending_next_episode, 'temp',
                new_ondeck, offdeck_list,
                unwatched_count, watched_count,
                is_skipped=False
            )
            
            self._log.debug(
                "Next episode prepared",
                episode_id=self._pending_next_episode,
                new_ondeck=new_ondeck
            )
            
            # Handle monitor override
            if self._state.monitor_override:
                self._log.debug("Monitor override: triggering swap (sequential show)")
                self._episode_tracker.transition_to_next_episode(self._current_show_id)
                self._state.monitor_override = False
                self._player._playing_epid = False
                self._state.target = False
                self._pending_next_episode = False
        else:
            # Last episode in list - mark show for removal
            self._log.debug("Last episode in list, marking show for removal")
            self._eject = True
    
    def _prepare_next_prompt_info(self) -> None:
        """
        Prepare next episode prompt information.
        
        If next prompts are enabled and we have a pending next episode,
        fetch the episode details for the prompt dialog.
        """
        if not self._settings.nextprompt:
            return
        if not self._pending_next_episode:
            return
        if self._eject:
            return
        if self._is_random_show:
            return
        
        cp_details = json_query(
            build_episode_prompt_info_query(int(self._pending_next_episode)), True
        )
        
        self._log.debug("Prompt episode details", details=cp_details)
        
        if 'episodedetails' in cp_details:
            self._state.nextprompt_info = cp_details['episodedetails']
    
    def _set_playback_target(self) -> None:
        """
        Set the playback position target for swap over.
        
        Polls for the video duration and calculates the target position
        (completion threshold) at which to swap episode data.
        """
        tick = 0
        while not self._state.target and tick < TARGET_DETECTION_MAX_TICKS:
            self._state.target = (
                runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration')) *
                self._playback_complete_threshold
            )
            tick += 1
            xbmc.sleep(TARGET_DETECTION_SLEEP_MS)
        
        self._log.debug(
            "Target detection complete",
            ticks=tick,
            target_seconds=self._state.target
        )
    
    def _check_playback_position(self) -> None:
        """
        Check playback position for swap over.
        
        Called every cycle when a target is set. Only actually checks
        position every POSITION_CHECK_INTERVAL_TICKS cycles to avoid
        excessive polling.
        """
        self._position_check_count = (
            (self._position_check_count + 1) % POSITION_CHECK_INTERVAL_TICKS
        )
        
        if self._position_check_count != 0:
            return
        
        current_position = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Time'))
        
        if current_position <= self._state.target:
            return
        
        self._log.debug(
            "Playback threshold exceeded",
            prompt_info=self._state.nextprompt_info
        )
        
        # Handle show completion (no more episodes)
        if self._eject:
            self._remove_from_shows_with_next_episodes(self._current_show_id)
            self._current_show_id = False
            self._eject = False
        
        # Perform swap over
        if self._current_show_id:
            self._episode_tracker.transition_to_next_episode(self._current_show_id)
            self._log.debug("Episode data swapped")
        
        # Trigger next episode prompt if configured
        if self._settings.nextprompt and self._state.nextprompt_info:
            self._log.debug("Next prompt trigger set")
            self._player._nextprompt_trigger = True
        
        # Reset state
        self._current_show_id = False
        self._pending_next_episode = False
        self._state.target = False
        self._state.monitor_override = False
    
    # =========================================================================
    # Show Management Methods
    # =========================================================================
    
    def _remove_from_shows_with_next_episodes(self, show_id: int) -> None:
        """
        Remove a show from the tracked shows list.
        
        Called when a show has no more unwatched episodes.
        Also updates smart playlists to remove the show.
        
        Args:
            show_id: The TV show ID to remove.
        """
        if show_id in self._state.shows_with_next_episodes:
            self._state.shows_with_next_episodes.remove(show_id)
            self._log.debug(
                "Show removed from tracking",
                show_id=show_id,
                total_tracked=len(self._state.shows_with_next_episodes)
            )
            self._window.setProperty(
                "EasyTV.shows_with_next_episodes",
                str(self._state.shows_with_next_episodes)
            )
        
        self._update_smartplaylist(show_id, remove=True)
    
    def _add_to_shows_with_next_episodes(self, show_id: int) -> None:
        """
        Add a show to the tracked shows list.
        
        Args:
            show_id: The TV show ID to add.
        """
        if show_id not in self._state.shows_with_next_episodes:
            self._state.shows_with_next_episodes.append(show_id)
            self._log.debug(
                "Show added to tracking",
                show_id=show_id,
                total_tracked=len(self._state.shows_with_next_episodes)
            )
            self._window.setProperty(
                "EasyTV.shows_with_next_episodes",
                str(self._state.shows_with_next_episodes)
            )
    
    def _reshuffle_random_order_shows(
        self,
        supplied_random_shows: Optional[list[int]] = None,
    ) -> None:
        """
        Reshuffle episodes for random-order shows.
        
        For each random-order show, picks a new random episode from
        the combined ondeck+offdeck pool and caches it.
        
        Args:
            supplied_random_shows: Specific shows to shuffle, or None for all.
        """
        self._log.debug("Shuffle started")
        
        if supplied_random_shows is None:
            shows_to_shuffle = self._settings.random_order_shows
        else:
            shows_to_shuffle = supplied_random_shows
        
        self._log.debug("Shows to shuffle", shows=shows_to_shuffle)
        
        for random_show in shows_to_shuffle:
            # Get ondeck and offdeck lists
            try:
                temp_ondeck_list = ast.literal_eval(
                    self._window.getProperty(f"EasyTV.{random_show}.ondeck_list")
                )
            except (ValueError, SyntaxError):
                temp_ondeck_list = []
            
            try:
                temp_offdeck_list = ast.literal_eval(
                    self._window.getProperty(f"EasyTV.{random_show}.offdeck_list")
                )
            except (ValueError, SyntaxError):
                temp_offdeck_list = []
            
            ep = self._window.getProperty(f"EasyTV.{random_show}.EpisodeID")
            
            if not ep:
                continue
            
            temp_watched_count = self._window.getProperty(
                f"EasyTV.{random_show}.CountWatchedEps"
            ).replace("''", '0')
            temp_unwatched_count = self._window.getProperty(
                f"EasyTV.{random_show}.CountUnwatchedEps"
            ).replace("''", '0')
            
            temp_combined_episodes = temp_ondeck_list + temp_offdeck_list
            if not temp_combined_episodes:
                continue
            
            # Choose new random episode
            random.shuffle(temp_combined_episodes)
            random_episode_id = temp_combined_episodes[0]
            
            # Cache the new random episode
            self._episode_tracker.cache_next_episode(
                random_episode_id, random_show,
                temp_ondeck_list, temp_offdeck_list,
                temp_unwatched_count, temp_watched_count,
                is_skipped=False
            )
        
        self._log.debug("Shuffle completed")
    
    def _regenerate_playlist(self) -> None:
        """
        Regenerate a random playlist from stored configuration.
        
        Called when the user accepts the playlist continuation prompt.
        Retrieves the stored config from window properties and rebuilds
        the playlist with the same settings.
        """
        self._log.info("Regenerating playlist", event="playlist.regenerate")
        
        # Get stored config
        config_json = self._window.getProperty(PROP_PLAYLIST_CONFIG)
        if not config_json:
            self._log.warning("No stored playlist config found")
            return
        
        try:
            playlist_state = json.loads(config_json)
        except (json.JSONDecodeError, ValueError) as e:
            self._log.warning("Failed to parse playlist config", error=str(e))
            self._window.clearProperty(PROP_PLAYLIST_CONFIG)
            return
        
        # Import here to avoid potential circular imports at module level
        from resources.lib.playback.random_player import (
            RandomPlaylistConfig,
            build_random_playlist,
        )
        
        # Reconstruct the config and population
        population = playlist_state.get('population', {'none': ''})
        random_order_shows = playlist_state.get('random_order_shows', [])
        config_dict = playlist_state.get('config', {})
        
        # Build config from stored dict
        config = RandomPlaylistConfig(
            length=config_dict.get('length', 10),
            playlist_content=config_dict.get('playlist_content', 1),
            episode_selection=config_dict.get('episode_selection', 0),
            movie_selection=config_dict.get('movie_selection', 0),
            movieweight=config_dict.get('movieweight', 0.5),
            start_partials_tv=config_dict.get('start_partials_tv', True),
            start_partials_movies=config_dict.get('start_partials_movies', True),
            premieres=config_dict.get('premieres', True),
            season_premieres=config_dict.get('season_premieres', True),
            multiple_shows=config_dict.get('multiple_shows', False),
            sort_by=config_dict.get('sort_by', 0),
            sort_reverse=config_dict.get('sort_reverse', False),
            language=config_dict.get('language', 'English'),
            movie_playlist=config_dict.get('movie_playlist'),
            unwatched_ratio=config_dict.get('unwatched_ratio', 50),
            duration_filter_enabled=config_dict.get('duration_filter_enabled', False),
            duration_min=config_dict.get('duration_min', 0),
            duration_max=config_dict.get('duration_max', 0),
        )
        
        # Rebuild the playlist
        build_random_playlist(
            population=population,
            random_order_shows=random_order_shows,
            config=config,
            logger=self._log
        )
        
        self._log.info("Playlist regenerated", event="playlist.regenerated")
    
    def _check_playlist_format_version(self) -> None:
        """
        Check playlist format version and migrate if needed.
        
        If the stored format version doesn't match the current version,
        deletes all existing playlists so they will be regenerated fresh
        during bulk_refresh.
        
        This ensures playlists are always in the current format after
        addon updates that change the playlist structure.
        """
        if not self._settings.maintainsmartplaylist:
            return
        
        stored_version = load_playlist_format_version()
        
        if stored_version != PLAYLIST_FORMAT_VERSION:
            self._log.info(
                "Playlist format version mismatch, migrating",
                event="playlist.version_mismatch",
                stored_version=stored_version,
                current_version=PLAYLIST_FORMAT_VERSION
            )
            
            # Delete old playlists
            deleted_count = delete_easytv_playlists()
            
            # Save new version (will be confirmed after bulk_refresh completes)
            addon_version = self._addon.getAddonInfo('version')
            save_playlist_format_version(PLAYLIST_FORMAT_VERSION, addon_version)
            
            self._log.info(
                "Playlist migration complete",
                event="playlist.migration_complete",
                deleted_count=deleted_count,
                new_version=PLAYLIST_FORMAT_VERSION
            )
        else:
            self._log.debug(
                "Playlist format version OK",
                version=PLAYLIST_FORMAT_VERSION
            )
    
    def _initial_library_scan(self) -> None:
        """
        Perform initial library scan with retry logic.
        
        On fresh addon install, the database may not be immediately accessible
        even if Kodi is running. This method retries the scan until shows are
        found or the maximum retries are exhausted.
        
        The scan will succeed immediately if:
        - Database is ready and has shows with unwatched episodes
        
        The scan will retry if:
        - Database returns empty results (may not be ready yet)
        
        The scan will give up if:
        - Maximum retries exhausted (user may have no unwatched episodes)
        - Kodi abort requested
        """
        self._log.debug("Starting initial library scan")
        
        # Check playlist format version before bulk refresh
        self._check_playlist_format_version()
        
        for attempt in range(DB_STARTUP_MAX_RETRIES):
            # Check for abort
            if self._monitor.abortRequested():
                self._log.debug("Library scan aborted")
                self._window.setProperty("EasyTV.shows_with_next_episodes", "[]")
                return
            
            # Query for shows with unwatched episodes
            result = json_query(get_unwatched_shows_query(), True)
            
            if 'tvshows' in result and len(result['tvshows']) > 0:
                # Found shows - populate the list
                self._all_shows_list = [
                    show['tvshowid'] for show in result['tvshows']
                ]
                self._log.info(
                    "Library scan complete",
                    event="service.library_ready",
                    shows_found=len(self._all_shows_list),
                    attempts=attempt + 1
                )
                # Load episode data for all shows
                self.refresh_show_episodes(showids=self._all_shows_list, bulk=True)
                return
            
            # No shows found - wait and retry
            if attempt < DB_STARTUP_MAX_RETRIES - 1:
                self._log.debug(
                    "No shows found, retrying",
                    attempt=attempt + 1,
                    max_attempts=DB_STARTUP_MAX_RETRIES
                )
                xbmc.sleep(DB_STARTUP_CHECK_INTERVAL_MS)
        
        # Exhausted retries - user may have no unwatched episodes
        self._log.info(
            "Library scan found no shows",
            event="service.library_empty",
            max_retries=DB_STARTUP_MAX_RETRIES
        )
        self._all_shows_list = []
        self._window.setProperty("EasyTV.shows_with_next_episodes", "[]")
    
    def _retrieve_all_show_ids(self) -> None:
        """
        Retrieve all TV show IDs from the Kodi library.
        
        Queries Kodi for all shows with unwatched episodes and
        stores their IDs in _all_shows_list.
        """
        with log_timing(self._log, "retrieve_show_ids"):
            result = json_query(get_unwatched_shows_query(), True)
            
            if 'tvshows' not in result:
                self._all_shows_list = []
            else:
                self._all_shows_list = [
                    show['tvshowid'] for show in result['tvshows']
                ]
            
            self._log.debug("TV shows retrieved", count=len(self._all_shows_list))
    
    def refresh_show_episodes(
        self,
        showids: list[int] | Optional[int] = None,
        bulk: bool = False,
    ) -> None:
        """
        Retrieve and process next episodes for the specified TV shows.
        
        Determines the "on-deck" episode for each show and stores
        all relevant metadata in Kodi window properties.
        
        Episode Classification (ondeck vs offdeck):
            - ondeck: Episodes that are sequential "next" episodes
            - offdeck: Unwatched episodes before current position (skipped)
        
        Episode Selection Logic:
            - Random shows: Combine ondeck + offdeck, shuffle, pick first
            - Sequential with ondeck: Pick first ondeck episode
            - Sequential with ONLY offdeck: Pick earliest skipped episode,
              mark as is_skipped=True for UI indication
        
        Args:
            showids: List of show IDs to process, single ID, or None.
            bulk: If True, suppress per-show debug logging (for startup/library scans).
        """
        # Normalize showids to a list
        if showids is None:
            showids = []
        showids = showids if isinstance(showids, list) else [showids]
        
        if not bulk:
            self._log.debug("Processing episodes for shows", show_count=len(showids))
        
        # Use timing context for both bulk and non-bulk operations
        timing_ctx = (
            log_timing(self._log, "bulk_refresh", show_count=len(showids))
            if bulk else log_timing(self._log, "show_refresh", show_count=len(showids))
        )
        
        with timing_ctx as timer:
            # Get shows sorted by last played
            lshows_result = json_query(get_shows_by_lastplayed_query(), True)
            
            if 'tvshows' not in lshows_result:
                show_lw = []
            else:
                show_lw = [
                    x['tvshowid'] for x in lshows_result['tvshows']
                    if x['tvshowid'] in showids
                ]
            
            # Mark end of show query phase
            if timer is not None:
                timer.mark("show_query")
            
            # For bulk operations, fetch all episodes in one query
            # Use the fast query without streamdetails - duration cache handles that separately
            episodes_by_show: Dict[int, List[Dict[str, Any]]] = {}
            if bulk and show_lw:
                showids_set = set(show_lw)
                all_episodes_result = json_query(build_all_episodes_no_streamdetails_query(), True)
                
                # Group episodes by show ID
                for ep in all_episodes_result.get('episodes', []):
                    show_id = ep['tvshowid']
                    if show_id in showids_set:
                        episodes_by_show.setdefault(show_id, []).append(ep)
            
            # Mark end of episode query phase
            if timer is not None:
                timer.mark("episode_query")
            
            # Start batch mode for playlist writes in bulk mode
            if bulk and self._settings.maintainsmartplaylist:
                start_playlist_batch()
            
            # Timing instrumentation for processing breakdown
            _proc_shows_iterated = 0
            _proc_shows_with_eps = 0
            _proc_cache_time_ms = 0
            _proc_logic_time_ms = 0
            
            for my_showid in show_lw:
                _proc_shows_iterated += 1
                _logic_start = time.perf_counter()
                service_heartbeat()
                
                # Get episodes: from pre-fetched bulk data or per-show query
                if bulk:
                    eps = episodes_by_show.get(my_showid, [])
                else:
                    ep_result = json_query(build_show_episodes_query(my_showid), True)
                    if 'episodes' not in ep_result:
                        continue
                    eps = ep_result['episodes']
                
                if not eps:
                    continue
                
                _proc_shows_with_eps += 1
                all_unplayed = []
                season = FIRST_REGULAR_SEASON
                episode = EPISODE_INITIAL_VALUE
                watched_showcount = 0
                on_deck_epid: Optional[int] = None
                
                # Find highest watched episode and collect unwatched
                for ep in eps:
                    if ep['playcount'] != 0:
                        watched_showcount += 1
                        if ((ep['season'] == season and ep['episode'] > episode) or
                                ep['season'] > season):
                            season = ep['season']
                            episode = ep['episode']
                    else:
                        all_unplayed.append(ep)
                
                # Sort by season/episode before dedup to ensure multi-episode files
                # consistently select the lowest episode number as representative
                all_unplayed.sort(key=lambda x: (x['season'], x['episode']))
                
                # Remove duplicate files (double episodes) using set for O(1) lookup
                seen_files: set[str] = set()
                unique_unplayed = []
                for ep in all_unplayed:
                    if ep['file'] and ep['file'] not in seen_files:
                        seen_files.add(ep['file'])
                        unique_unplayed.append(ep)
                all_unplayed = unique_unplayed
                del seen_files, unique_unplayed
                
                # Separate into ondeck and offdeck
                unordered_ondeck_eps = [
                    x for x in all_unplayed
                    if x['season'] > season or
                    (x['season'] == season and x['episode'] > episode)
                ]
                # Use set for O(1) lookup instead of O(n) list membership
                ondeck_ep_ids = {ep['episodeid'] for ep in unordered_ondeck_eps}
                offdeck_eps = [
                    x for x in all_unplayed
                    if x['episodeid'] not in ondeck_ep_ids
                ]
                
                # Calculate counts
                count_eps = len(eps)
                count_weps = watched_showcount
                count_uweps = count_eps - count_weps
                
                # Sort ondeck by season/episode
                ondeck_eps = [
                    ep for ep in sorted(unordered_ondeck_eps, key=lambda x: (x['season'], x['episode']))
                    if ep
                ]
                
                if not ondeck_eps and not offdeck_eps:
                    if my_showid in self._state.shows_with_next_episodes:
                        self._remove_from_shows_with_next_episodes(my_showid)
                    continue
                
                # Determine if this is a skipped episode selection
                is_skipped_episode = False
                selected_ep_data: Optional[Dict[str, Any]] = None
                
                # Select the next episode
                if my_showid in self._settings.random_order_shows:
                    # Random shows: combine and shuffle all episodes
                    combined_deck_list = ondeck_eps + offdeck_eps
                    random.shuffle(combined_deck_list)
                    on_deck_epid = combined_deck_list[0]['episodeid']
                    selected_ep_data = combined_deck_list[0] if bulk else None
                elif ondeck_eps:
                    # Sequential show with ondeck episodes: pick first
                    on_deck_epid = ondeck_eps[0]['episodeid']
                    selected_ep_data = ondeck_eps[0] if bulk else None
                else:
                    # Sequential show with ONLY offdeck episodes: pick earliest skipped
                    # (offdeck_eps is already sorted by season/episode from earlier sort)
                    on_deck_epid = offdeck_eps[0]['episodeid']
                    selected_ep_data = offdeck_eps[0] if bulk else None
                    is_skipped_episode = True
                    if not bulk:
                        self._log.debug(
                            "Selecting skipped episode (no ondeck available)",
                            show_id=my_showid,
                            episode_id=on_deck_epid
                        )
                
                # Build episode ID lists
                on_deck_list = [
                    x['episodeid'] for x in ondeck_eps
                ] if ondeck_eps else []
                off_deck_list = [
                    x['episodeid'] for x in offdeck_eps
                ] if offdeck_eps else []
                
                # Track logic time (everything before cache)
                _proc_logic_time_ms += int((time.perf_counter() - _logic_start) * 1000)
                
                # Cache episode data in window properties
                _cache_start = time.perf_counter()
                self._episode_tracker.cache_next_episode(
                    on_deck_epid, my_showid,
                    on_deck_list, off_deck_list,
                    count_uweps, count_weps,
                    is_skipped=is_skipped_episode,
                    quiet=bulk,
                    ep_data=selected_ep_data
                )
                _proc_cache_time_ms += int((time.perf_counter() - _cache_start) * 1000)
                
                # Add to tracked shows
                if my_showid not in self._state.shows_with_next_episodes:
                    self._state.shows_with_next_episodes.append(my_showid)
            
            # Log processing breakdown
            if bulk:
                self._log.debug(
                    "Processing loop breakdown",
                    shows_iterated=_proc_shows_iterated,
                    shows_with_episodes=_proc_shows_with_eps,
                    logic_ms=_proc_logic_time_ms,
                    cache_ms=_proc_cache_time_ms
                )
            
            # Mark end of main processing loop (for bulk timing breakdown)
            if timer is not None:
                timer.mark("processing")
            
            # Cache episode duration for each show (bulk mode only)
            # Uses persistent cache to avoid querying streamdetails for every show
            if bulk and episodes_by_show:
                # Load existing cache
                duration_cache = load_duration_cache()
                
                # Count episodes per show
                current_episode_counts: Dict[int, int] = {
                    show_id: len(eps) for show_id, eps in episodes_by_show.items()
                }
                
                # Extract show titles from first episode of each show (for cache readability)
                show_titles: Dict[int, str] = {
                    show_id: eps[0].get('showtitle', '')
                    for show_id, eps in episodes_by_show.items()
                    if eps
                }
                
                # Determine which shows need duration recalculation
                shows_needing_calc = get_shows_needing_calculation(
                    duration_cache, current_episode_counts
                )
                
                if timer is not None:
                    timer.mark("duration_compare")
                
                # Query streamdetails only for shows that need recalculation
                new_durations: Dict[int, int] = {}
                if shows_needing_calc:
                    for show_id in shows_needing_calc:
                        service_heartbeat()
                        # Query this show's episodes with streamdetails
                        ep_result = json_query(
                            build_show_episodes_with_streamdetails_query(show_id),
                            True
                        )
                        episodes_with_stream = ep_result.get('episodes', [])
                        # Calculate median duration
                        median = calculate_median_duration(episodes_with_stream)
                        new_durations[show_id] = median
                    
                    self._log.debug(
                        "Duration recalculation complete",
                        shows_recalculated=len(shows_needing_calc),
                        shows_from_cache=len(current_episode_counts) - len(shows_needing_calc)
                    )
                
                if timer is not None:
                    timer.mark("duration_calc")
                
                # Build updated cache (merges old + new, prunes removed shows)
                updated_cache = build_updated_cache(
                    duration_cache, current_episode_counts, new_durations, show_titles
                )
                
                # Write all durations to window properties
                cached_shows = updated_cache.get('shows', {})
                for show_id in current_episode_counts.keys():
                    show_id_str = str(show_id)
                    if show_id_str in cached_shows:
                        duration = cached_shows[show_id_str].get('median_seconds', 0)
                    elif show_id in new_durations:
                        # Show calculated but not cached (median was 0)
                        duration = new_durations[show_id]
                    else:
                        duration = 0
                    prop_key = f"EasyTV.{show_id}.{PROP_DURATION}"
                    self._window.setProperty(prop_key, str(duration))
                
                # Save updated cache
                save_duration_cache(updated_cache)
                
                self._log.debug(
                    "Duration cache updated",
                    total_shows=len(current_episode_counts),
                    cached_shows=len(cached_shows),
                    shows_recalculated=len(new_durations)
                )
                
                if timer is not None:
                    timer.mark("duration_save")
            
            # Flush batched playlist writes
            if bulk and self._settings.maintainsmartplaylist:
                flush_playlist_batch()
                if timer is not None:
                    timer.mark("playlists")
            
            # Update window property with tracked shows
            self._window.setProperty(
                "EasyTV.shows_with_next_episodes",
                str(self._state.shows_with_next_episodes)
            )
        
        if not bulk:
            self._log.debug("Episode processing complete")
    
    # =========================================================================
    # Smart Playlist Management
    # =========================================================================
    
    def _update_smartplaylist(
        self,
        tvshowid: Union[int, str],
        remove: bool = False,
        quiet: bool = False,
    ) -> None:
        """
        Update smart playlists for a TV show.
        
        Maintains five smart playlists:
        - "All Shows": Every show with an ondeck episode
        - "Continue Watching": Shows where next episode > 1
        - "Start Fresh": Shows where next episode = 1
        - "Show Premieres": Shows at S01E01 (brand new shows)
        - "Season Premieres": Shows at S02E01+ (new season)
        
        Args:
            tvshowid: The TV show ID.
            remove: If True, remove show from all playlists.
            quiet: If True, suppress debug logging (for bulk operations).
        """
        if not self._settings.maintainsmartplaylist or tvshowid == 'temp':
            return
        
        # Ensure tvshowid is an integer for playlist operations
        try:
            show_id = int(tvshowid)
        except (ValueError, TypeError):
            if not quiet:
                self._log.debug(
                    "Smart playlist update skipped - invalid show ID",
                    show_id=tvshowid
                )
            return
        
        show_data = fetch_show_episode_data(show_id)
        if not show_data:
            if not quiet:
                self._log.debug(
                    "Smart playlist update skipped - no show data",
                    show_id=show_id
                )
            return
        
        filename = show_data['filename']
        episode_number = show_data['episode_number']
        season_number = show_data['season_number']
        episodeno = show_data['episodeno']
        
        if remove:
            remove_show_from_all_playlists(
                show_id,
                PLAYLIST_ALL_SHOWS, PLAYLIST_NAME_ALL_SHOWS,
                PLAYLIST_CONTINUE_WATCHING, PLAYLIST_NAME_CONTINUE_WATCHING,
                PLAYLIST_START_FRESH, PLAYLIST_NAME_START_FRESH,
                PLAYLIST_SHOW_PREMIERES, PLAYLIST_NAME_SHOW_PREMIERES,
                PLAYLIST_SEASON_PREMIERES, PLAYLIST_NAME_SEASON_PREMIERES,
                quiet=quiet
            )
            if not quiet:
                self._log.debug(
                    "Show removed from smart playlists",
                    show_id=show_id
                )
        else:
            category = get_show_category(episode_number)
            premiere_category = get_premiere_category(season_number, episode_number)
            
            update_show_in_playlists(
                show_id, filename, category, premiere_category,
                PLAYLIST_ALL_SHOWS, PLAYLIST_NAME_ALL_SHOWS,
                PLAYLIST_CONTINUE_WATCHING, PLAYLIST_NAME_CONTINUE_WATCHING,
                PLAYLIST_START_FRESH, PLAYLIST_NAME_START_FRESH,
                PLAYLIST_SHOW_PREMIERES, PLAYLIST_NAME_SHOW_PREMIERES,
                PLAYLIST_SEASON_PREMIERES, PLAYLIST_NAME_SEASON_PREMIERES,
                CATEGORY_START_FRESH,
                CATEGORY_SHOW_PREMIERE,
                CATEGORY_SEASON_PREMIERE,
                episodeno=episodeno,
                quiet=quiet
            )
            if not quiet:
                self._log.debug(
                    "Show added to smart playlists",
                    show_id=show_id,
                    category=category,
                    premiere_category=premiere_category,
                    episode=episodeno
                )
    
    # =========================================================================
    # Settings and Callbacks
    # =========================================================================
    
    def _get_playback_settings(self) -> PlaybackSettings:
        """
        Get current playback settings for PlaybackMonitor.
        
        Returns:
            PlaybackSettings with current configuration.
        """
        return PlaybackSettings(
            previous_episode_check=self._settings.previous_episode_check,
            nextprompt=self._settings.nextprompt,
            nextprompt_in_playlist=self._settings.nextprompt_in_playlist,
            playlist_notifications=self._settings.playlist_notifications,
            resume_partials_tv=self._settings.resume_partials_tv,
            resume_partials_movies=self._settings.resume_partials_movies,
            movies_random_start=get_bool_setting('movies_random_start'),
            promptdefaultaction=self._settings.promptdefaultaction,
            promptduration=self._settings.promptduration,
            playlist_continuation=self._settings.playlist_continuation,
            playlist_continuation_duration=self._settings.playlist_continuation_duration,
        )
    
    def _on_settings_changed(self) -> None:
        """
        Handle settings changes from LibraryMonitor.
        
        Reloads all settings and updates component configurations.
        """
        # Store old maintainsmartplaylist value before reload
        old_maintainsmartplaylist = self._settings.maintainsmartplaylist
        
        self._settings = load_settings(
            firstrun=False,
            window=self._window,
            addon=self._addon,
            logger=self._log,
            on_add_random_show=self._add_to_shows_with_next_episodes,
            on_reshuffle_random_shows=self._reshuffle_random_order_shows,
            on_store_next_ep=self._episode_tracker.cache_next_episode,
            on_remove_show=self._remove_from_shows_with_next_episodes,
            on_update_smartplaylist=self._update_smartplaylist,
            shows_with_next_episodes=self._state.shows_with_next_episodes,
        )
        
        # Check if smart playlist setting was just enabled
        # Now self._settings has the new value, so _update_smartplaylist will work
        if not old_maintainsmartplaylist and self._settings.maintainsmartplaylist:
            self._log.info(
                "Smart playlist enabled, updating all shows",
                event="smartplaylist.enable",
                show_count=len(self._state.shows_with_next_episodes)
            )
            for show_id in self._state.shows_with_next_episodes:
                self._update_smartplaylist(show_id, quiet=True)
    
    def load_initial_settings(self) -> None:
        """
        Load initial settings at service startup.
        
        Called before initialize() to ensure settings are available
        for component creation.
        """
        self._settings = load_settings(
            firstrun=True,
            window=self._window,
            addon=self._addon,
            logger=self._log,
            on_add_random_show=self._add_to_shows_with_next_episodes,
            on_reshuffle_random_shows=self._reshuffle_random_order_shows,
            on_store_next_ep=lambda *args: None,  # Not ready yet
            on_remove_show=self._remove_from_shows_with_next_episodes,
            on_update_smartplaylist=lambda *args: None,  # Not ready yet
            shows_with_next_episodes=self._state.shows_with_next_episodes,
        )
        
        self._log.info("Initial settings loaded", event="settings.load")
