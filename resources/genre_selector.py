#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#
"""Genre preset picker for the guided questions settings.

Invoked from settings via RunScript(script.easytv,guided_genres,<kind>)
where <kind> is 'ignore' or 'include'. Shows the themed multiselect over
the library's genres and stores the choice in the matching preset
setting (JSON list) plus its display sibling.

Logging:
    Logger: 'selector'
    Key events:
        - selector.genres_open (DEBUG): Picker opened
        - selector.genres_save (INFO): Selection saved
    See LOGGING.md for full guidelines.
"""
import json
import sys

import xbmcaddon

from resources.lib.data.show_filters import (
    extract_unique_genres,
    fetch_filterable_shows,
)
from resources.lib.ui.dialogs import show_multi_select
from resources.lib.ui.wizard import _parse_genre_list
from resources.lib.utils import get_logger, lang

log = get_logger('selector')

_SETTINGS = {
    'ignore': ('guided_preset_ignore_genres',
               'guided_preset_ignore_genres_display', 32770),
    'include': ('guided_preset_genres',
                'guided_preset_genres_display', 32771),
}


def Main() -> None:
    addon = xbmcaddon.Addon()
    addon_id = addon.getAddonInfo('id')

    kind = sys.argv[2] if len(sys.argv) > 2 else 'include'
    setting_id, display_id, heading_id = _SETTINGS.get(
        kind, _SETTINGS['include'])
    log.debug("Genre preset picker opened",
              event="selector.genres_open", kind=kind)

    genres = extract_unique_genres(fetch_filterable_shows())
    if not genres:
        log.warning("No genres in library", event="selector.genres_open")
        return

    saved = _parse_genre_list(addon.getSetting(setting_id))
    preselected = [i for i, g in enumerate(genres) if g in saved]

    result = show_multi_select(lang(heading_id, addon_id), genres,
                               preselected=preselected, addon_id=addon_id)
    if result is None:
        return  # cancelled

    selected = [genres[i] for i in result]
    addon.setSetting(setting_id, json.dumps(selected) if selected else 'none')
    addon.setSetting(display_id, ", ".join(selected) if selected else '-')
    log.info("Genre preset saved", event="selector.genres_save",
             kind=kind, count=len(selected))
