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
EasyTV Background Service Entry Point.

Monitors playback, updates episode tracking, and provides next episode prompts.
Modernized for Kodi 21+ (Nexus/Omega).

Logging:
    Module: service
    Events:
        - service.start (INFO): Service has started
        - service.stop (INFO): Service has stopped
"""

import xbmcaddon
from resources.lib.utils import get_logger, parse_version, StructuredLogger
from resources.lib.service.daemon import ServiceDaemon

if __name__ == "__main__":
    addon = xbmcaddon.Addon()
    version_str = addon.getAddonInfo('version')
    version = parse_version(version_str)
    log = get_logger('service')

    log.info("Service started", event="service.start", version=version_str)

    daemon = ServiceDaemon(addon=addon, logger=log)
    daemon.load_initial_settings()
    daemon.initialize()
    daemon.run()

    log.info("Service stopped", event="service.stop", version=version_str)
    StructuredLogger.shutdown()
