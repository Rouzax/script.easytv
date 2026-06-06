#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
Streamdetails Cache for EasyTV.

Stores per-episode stream information (duration, resolution, audio codec,
channels, subtitle languages) extracted from Kodi's streamdetails queries.
This cache piggybacks on the same queries the duration cache uses for median
calculation, so it adds zero extra JSON-RPC calls.

Kodi's JSON-RPC returns ``runtime: 0`` for episodes unless ``streamdetails``
is also requested, and adding ``streamdetails`` to the bulk episode query
costs ~11 extra seconds on large libraries. This cache avoids that cost by
persisting the data across restarts and only requerying shows whose episode
count has changed.

Cache File:
    Location: special://profile/addon_data/script.easytv/streamdetails_cache.json

    Format:
        {
            "version": 1,
            "shows": {
                "123": {
                    "episode_count": 45,
                    "episodes": {
                        "1001": {
                            "duration": 2640,
                            "resolution": "1080p",
                            "video_codec": "h264",
                            "hdr": "",
                            "audio_codec": "eac3",
                            "channels": 6,
                            "subtitles": ["eng", "dut"]
                        }
                    }
                }
            }
        }

Logging:
    Logger: 'data' (via get_logger)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set

import xbmcvfs

from resources.lib.constants import (
    DEFAULT_ADDON_ID,
    STREAMDETAILS_CACHE_FILENAME,
    STREAMDETAILS_CACHE_VERSION,
)
from resources.lib.utils import get_logger


log = get_logger('data')

_cache_file_path: Optional[str] = None


def get_cache_file_path() -> str:
    """Get the streamdetails cache file path, creating the directory if needed."""
    global _cache_file_path
    if _cache_file_path is None:
        cache_dir = xbmcvfs.translatePath(
            f"special://profile/addon_data/{DEFAULT_ADDON_ID}/"
        )
        if not xbmcvfs.exists(cache_dir):
            xbmcvfs.mkdirs(cache_dir)
        _cache_file_path = os.path.join(cache_dir, STREAMDETAILS_CACHE_FILENAME)
    return _cache_file_path


def load_streamdetails_cache() -> Dict[str, Any]:
    """
    Load the streamdetails cache from disk.

    Returns empty cache on missing file, corruption, or version mismatch.
    """
    cache_path = get_cache_file_path()

    if not xbmcvfs.exists(cache_path):
        log.debug("Streamdetails cache file not found, starting fresh")
        return _empty_cache()

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict):
            log.warning("Streamdetails cache invalid structure, starting fresh")
            return _empty_cache()

        version = data.get('version', 0)
        if version != STREAMDETAILS_CACHE_VERSION:
            log.warning(
                "Streamdetails cache version mismatch",
                file_version=version,
                expected_version=STREAMDETAILS_CACHE_VERSION
            )
            return _empty_cache()

        if 'shows' not in data or not isinstance(data['shows'], dict):
            log.warning("Streamdetails cache missing shows dict, starting fresh")
            return _empty_cache()

        show_count = len(data['shows'])
        ep_count = sum(
            len(s.get('episodes', {})) for s in data['shows'].values()
        )
        log.debug(
            "Streamdetails cache loaded",
            show_count=show_count,
            episode_count=ep_count
        )
        return data

    except json.JSONDecodeError as e:
        log.warning("Streamdetails cache corrupted", error=str(e))
        return _empty_cache()
    except (OSError, IOError) as e:
        log.warning("Streamdetails cache read error", error=str(e))
        return _empty_cache()


def save_streamdetails_cache(cache: Dict[str, Any]) -> bool:
    """Save the streamdetails cache to disk. Returns True on success."""
    cache_path = get_cache_file_path()
    cache['version'] = STREAMDETAILS_CACHE_VERSION

    try:
        json_data = json.dumps(cache, indent=2)

        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(json_data)

        show_count = len(cache.get('shows', {}))
        ep_count = sum(
            len(s.get('episodes', {}))
            for s in cache.get('shows', {}).values()
        )
        log.debug(
            "Streamdetails cache saved",
            show_count=show_count,
            episode_count=ep_count
        )
        return True

    except (OSError, IOError, TypeError) as e:
        log.warning("Streamdetails cache save failed", error=str(e))
        return False


def format_resolution(height: int) -> str:
    """
    Map video height to a resolution label.

    Returns "2160p", "1080p", "720p", "480p", or "" for invalid values.
    """
    if height <= 0:
        return ''
    if height >= 2160:
        return '2160p'
    if height >= 1080:
        return '1080p'
    if height >= 720:
        return '720p'
    return '480p'


def extract_episode_streamdetails(
    episodes: List[Dict[str, Any]]
) -> Dict[int, Dict[str, Any]]:
    """
    Extract stream info from a list of episodes with streamdetails.

    Args:
        episodes: Episode dicts from ``build_show_episodes_with_streamdetails_query``.
                  Each must contain ``episodeid`` and ``streamdetails``.

    Returns:
        Dict mapping episode_id (int) to extracted stream info.
        Episodes without ``episodeid`` or without video streams are skipped.
    """
    result: Dict[int, Dict[str, Any]] = {}

    for ep in episodes:
        ep_id = ep.get('episodeid')
        if ep_id is None:
            continue

        stream = ep.get('streamdetails')
        if not stream:
            continue

        video_streams = stream.get('video', [])
        if not video_streams:
            continue

        video = video_streams[0]
        audio_streams = stream.get('audio', [])
        audio = audio_streams[0] if audio_streams else {}
        subtitle_streams = stream.get('subtitle', [])

        # Deduplicate subtitle languages while preserving order
        seen_langs: Set[str] = set()
        subtitles: List[str] = []
        for sub in subtitle_streams:
            lang = sub.get('language', '')
            if lang and lang not in seen_langs:
                seen_langs.add(lang)
                subtitles.append(lang)

        result[int(ep_id)] = {
            'duration': video.get('duration', 0),
            'resolution': format_resolution(video.get('height', 0)),
            'video_codec': video.get('codec', ''),
            'hdr': video.get('hdrtype', ''),
            'audio_codec': audio.get('codec', ''),
            'channels': audio.get('channels', 0),
            'subtitles': subtitles,
        }

    return result


def get_shows_needing_streamdetails(
    cache: Dict[str, Any],
    current_episode_counts: Dict[int, int]
) -> Set[int]:
    """
    Determine which shows need their streamdetails requeried.

    A show needs requerying if it is not in the cache, its episode count
    changed, or it has no episode data stored.
    """
    needs_query: Set[int] = set()
    cached_shows = cache.get('shows', {})

    for show_id, episode_count in current_episode_counts.items():
        show_id_str = str(show_id)

        if show_id_str not in cached_shows:
            needs_query.add(show_id)
            continue

        cached_data = cached_shows[show_id_str]
        cached_count = cached_data.get('episode_count', 0)

        if episode_count != cached_count:
            needs_query.add(show_id)
            continue

        cached_episodes = cached_data.get('episodes')
        if not cached_episodes:
            needs_query.add(show_id)

    cached_count = len(current_episode_counts) - len(needs_query)
    log.debug(
        "Streamdetails cache comparison",
        total_shows=len(current_episode_counts),
        cached_shows=cached_count,
        needs_query=len(needs_query)
    )

    return needs_query


def build_updated_streamdetails_cache(
    old_cache: Dict[str, Any],
    current_episode_counts: Dict[int, int],
    new_data: Dict[int, Dict[int, Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Build an updated cache merging old entries with new extractions.

    Args:
        old_cache: Previously loaded cache.
        current_episode_counts: Show ID to current episode count.
        new_data: Show ID to {episode_id: streamdetails_dict} for requeried shows.
    """
    new_cache = _empty_cache()
    old_shows = old_cache.get('shows', {})

    for show_id, episode_count in current_episode_counts.items():
        show_id_str = str(show_id)

        if show_id in new_data:
            new_cache['shows'][show_id_str] = {
                'episode_count': episode_count,
                'episodes': {
                    str(ep_id): ep_info
                    for ep_id, ep_info in new_data[show_id].items()
                },
            }
        elif show_id_str in old_shows:
            old_entry = old_shows[show_id_str].copy()
            new_cache['shows'][show_id_str] = old_entry

    return new_cache


def get_episode_duration(
    cache: Dict[str, Any],
    show_id: int,
    episode_id: int
) -> int:
    """
    Look up an episode's duration from the cache.

    Returns duration in seconds, or 0 if not found.
    """
    show_data = cache.get('shows', {}).get(str(show_id))
    if not show_data:
        return 0

    ep_data = show_data.get('episodes', {}).get(str(episode_id))
    if not ep_data:
        return 0

    return ep_data.get('duration', 0)


def _empty_cache() -> Dict[str, Any]:
    """Create an empty cache structure."""
    return {
        'version': STREAMDETAILS_CACHE_VERSION,
        'shows': {}
    }
