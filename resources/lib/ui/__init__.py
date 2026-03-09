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
EasyTV User Interface Components.

This package provides UI functionality:
- browse_window.py: BrowseWindow class (main episode list window)
- context_menu.py: ContextMenuWindow class (right-click menu)
- dialogs.py: Dialog helper functions (error dialogs, playlist selection)
"""
from __future__ import annotations

import xbmcgui


def apply_theme(window: xbmcgui.WindowXMLDialog) -> None:
    """Set theme color properties on a window for skin XML $INFO references."""
    import xbmcaddon
    from resources.lib.constants import THEME_COLORS
    theme = xbmcaddon.Addon().getSetting('theme') or '0'
    for prop, value in THEME_COLORS.get(theme, THEME_COLORS['0']).items():
        window.setProperty(prop, value)
