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
EasyTV constants - centralized magic values.

This module consolidates all hardcoded values from throughout the codebase
to improve maintainability and make the code self-documenting.
"""

# =============================================================================
# Episode Selection Modes (parallel to movie_selection)
# =============================================================================
EPISODE_SELECTION_UNWATCHED = 0
EPISODE_SELECTION_WATCHED = 1
EPISODE_SELECTION_BOTH = 2

# =============================================================================
# Kodi Window IDs
# =============================================================================
KODI_HOME_WINDOW_ID = 10000
KODI_FULLSCREEN_VIDEO_WINDOW_ID = 12005

# =============================================================================
# Timing Constants (milliseconds)
# =============================================================================
# Main loops
DAEMON_LOOP_SLEEP_MS = 100
MAIN_LOOP_SLEEP_MS = 100

# Playlist operations
PLAYLIST_START_DELAY_MS = 500
PLAYLIST_ADD_DELAY_MS = 50

# Player operations
PLAYER_STOP_DELAY_MS = 100
TARGET_DETECTION_SLEEP_MS = 250

# UI operations
NOTIFICATION_DURATION_MS = 5000
CONTEXT_TOGGLE_DELAY_MS = 500
DIALOG_WAIT_SLEEP_MS = 100

# Addon operations
ADDON_ENABLE_DELAY_MS = 1000
ADDON_RESTART_DELAY_MS = 1000

# File/Service operations
SERVICE_POLL_SLEEP_MS = 10
FILE_WRITE_DELAY_MS = 10
EXPORT_COMPLETE_DELAY_MS = 100

# =============================================================================
# Timing Constants (counts/ticks)
# =============================================================================
TARGET_DETECTION_MAX_TICKS = 20
POSITION_CHECK_INTERVAL_TICKS = 50
SERVICE_POLL_TIMEOUT_TICKS = 500
DIALOG_WAIT_MAX_TICKS = 5
ISTREAM_FIX_MAX_RETRIES = 2

# Database startup timing
DB_STARTUP_CHECK_INTERVAL_MS = 1000  # Check every 1 second
DB_STARTUP_MAX_RETRIES = 30  # Wait up to 30 seconds for DB

# =============================================================================
# Playback Thresholds
# =============================================================================
# Default threshold for considering playback "complete" (90%)
# Note: This should ideally be read from Kodi's advancedsettings.xml
# using get_playcount_minimum_percent() for user customization
PLAYBACK_COMPLETE_THRESHOLD_DEFAULT = 0.90

# Maximum ratio into a movie for random seek start point
MOVIE_RANDOM_SEEK_MAX_RATIO = 0.75

# Minimum percentage into a movie for random seek (skip opening credits)
MOVIE_RANDOM_SEEK_MIN_PERCENT = 5

# Random percentage range for movie seek
RANDOM_PERCENT_MAX = 100

# Seconds to rewind when resuming playback (helps catch context)
RESUME_REWIND_SECONDS = 10

# =============================================================================
# Episode/Playcount Constants
# =============================================================================
# Season 1 - used to ignore specials (Season 0)
FIRST_REGULAR_SEASON = 1

# Initial episode value before finding actual episode
EPISODE_INITIAL_VALUE = 0

# Playcount value indicating "watched"
WATCHED_PLAYCOUNT = 1

# =============================================================================
# Smart Playlist Configuration
# =============================================================================
# Format version for playlist migration (increment when format changes)
PLAYLIST_FORMAT_VERSION = 2
PLAYLIST_FORMAT_FILENAME = "playlist_format.json"

# Playlist filenames (stored in special://profile/playlists/video/)
PLAYLIST_ALL_SHOWS = "EasyTV - All Shows.xsp"
PLAYLIST_CONTINUE_WATCHING = "EasyTV - Continue Watching.xsp"
PLAYLIST_START_FRESH = "EasyTV - Start Fresh.xsp"
PLAYLIST_SHOW_PREMIERES = "EasyTV - Show Premieres.xsp"
PLAYLIST_SEASON_PREMIERES = "EasyTV - Season Premieres.xsp"

# Display names for playlists (shown in Kodi's playlist browser)
PLAYLIST_NAME_ALL_SHOWS = "EasyTV - All Shows"
PLAYLIST_NAME_CONTINUE_WATCHING = "EasyTV - Continue Watching"
PLAYLIST_NAME_START_FRESH = "EasyTV - Start Fresh"
PLAYLIST_NAME_SHOW_PREMIERES = "EasyTV - Show Premieres"
PLAYLIST_NAME_SEASON_PREMIERES = "EasyTV - Season Premieres"

# Episode threshold for categorization
# Episode 1 (any season) = "Start Fresh", Episode > 1 = "Continue Watching"
# S01E01 = "Show Premiere", S02E01+ = "Season Premiere"
SEASON_START_EPISODE = 1

# Category identifiers (returned by categorization logic)
CATEGORY_START_FRESH = "start_fresh"
CATEGORY_CONTINUE_WATCHING = "continue_watching"
CATEGORY_SHOW_PREMIERE = "show_premiere"
CATEGORY_SEASON_PREMIERE = "season_premiere"

# XML template components for smart playlist files
# Header: XML declaration + smartplaylist open + name + match rule
PLAYLIST_XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><smartplaylist type="episodes"><n>{name}</n><match>one</match>\n'
# Footer: order rule + smartplaylist close
PLAYLIST_XML_FOOTER = '<order direction="ascending">random</order></smartplaylist>'
# Show entry: comment-wrapped rule for a single show's episode
# Format: <!--show_id--><rule...>filename</rule>
PLAYLIST_XML_SHOW_ENTRY = '<!--{show_id}--><rule field="filename" operator="is"> <value>{filename}</value> </rule>\n'

# =============================================================================
# Limits
# =============================================================================
# Maximum items in list views
MAX_ITEMS_HARD_LIMIT = 1000

# Initial loop limit for iStream fix
INITIAL_LOOP_LIMIT = 10

# Value to break out of playlist building loop
PLAYLIST_BUILD_BREAK_VALUE = 99999

# =============================================================================
# Time Conversions
# =============================================================================
SECONDS_PER_MINUTE = 60
SECONDS_PER_DAY = 86400.0
SECONDS_TO_MS_MULTIPLIER = 1000
PERCENT_MULTIPLIER = 100

# Decimal places for day calculations
DAYS_DECIMAL_PLACES = 1

# Singular day value for grammar check
SINGULAR_DAY_VALUE = 1.0

# =============================================================================
# Candidate Type Prefixes
# =============================================================================
# Used in random playlist to distinguish TV shows from movies
TV_CANDIDATE_PREFIX = 't'
MOVIE_CANDIDATE_PREFIX = 'm'

# =============================================================================
# Kodi Action IDs
# =============================================================================
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117
ACTION_SELECT_ITEM = 7

# =============================================================================
# Context Menu Control IDs
# =============================================================================
CONTEXT_TOGGLE_MULTISELECT = 110
CONTEXT_PLAY_SELECTION = 120
CONTEXT_PLAY_FROM_HERE = 130
CONTEXT_EXPORT_SELECTION = 140
CONTEXT_TOGGLE_WATCHED = 150
CONTEXT_IGNORE_SHOW = 160
CONTEXT_UPDATE_LIBRARY = 170
CONTEXT_REFRESH = 180

# =============================================================================
# Standard Dialog/Window Control IDs
# =============================================================================
CONTROL_OK_BUTTON = 5
CONTROL_HEADING = 1
CONTROL_LIST = 6

# =============================================================================
# String Utilities
# =============================================================================
# Length of "The " for sorting (to strip leading article)
ARTICLE_THE_LENGTH = 4

# =============================================================================
# Movie Weight
# =============================================================================
# Weight value when movies are disabled
NO_MOVIE_WEIGHT = 0.0

# =============================================================================
# Logging Configuration
# =============================================================================
# Log file settings
LOG_DIR_NAME = "logs"
LOG_FILENAME = "easytv.log"
LOG_MAX_SIZE_BYTES = 512 * 1024  # 500KB per file
LOG_MAX_ROTATED_FILES = 3  # Keep 3 old log files

# Log format settings
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
LOG_TIMESTAMP_TRIM = -3  # Trim microseconds to milliseconds (remove last 3 chars)
LOG_MAX_VALUE_LENGTH = 200  # Truncate long values in log output

# Default addon ID (fallback when context unavailable)
DEFAULT_ADDON_ID = "script.easytv"

# =============================================================================
# Playlist Continuation Window Properties
# =============================================================================
# JSON-encoded config for regenerating playlist
PROP_PLAYLIST_CONFIG = "EasyTV.playlist_config"
# Flag to trigger playlist regeneration from daemon
PROP_PLAYLIST_REGENERATE = "EasyTV.playlist_regenerate"

# =============================================================================
# Browse Mode Window Properties
# =============================================================================
# Session flag indicating show art has been fetched (cleared on library scan)
PROP_ART_FETCHED = "EasyTV.ArtFetched"

# =============================================================================
# Duration Filter Settings
# =============================================================================
SETTING_DURATION_FILTER_ENABLED = "duration_filter_enabled"
SETTING_DURATION_MIN = "duration_min"
SETTING_DURATION_MAX = "duration_max"

# =============================================================================
# Duration Cache
# =============================================================================
# Cache file for storing median episode durations per show
DURATION_CACHE_FILENAME = "duration_cache.json"
# Schema version for cache file format (increment on breaking changes)
DURATION_CACHE_VERSION = 1

# =============================================================================
# Lazy Queue (Both Mode) Settings
# =============================================================================
# JSON-encoded session state for lazy queue playlist
PROP_LAZY_QUEUE_SESSION = "EasyTV.lazy_queue_session"
# Number of items to maintain in playlist buffer
LAZY_QUEUE_BUFFER_SIZE = 3
