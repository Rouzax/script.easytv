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
EasyTV Clone Update

This module updates an existing clone to match the current main EasyTV version.

Update Process:
    1. Trigger:
       - When a clone is launched, it compares its version to the service version
       - If out of date, user is prompted to update
       - This script is called with: src_path, new_path, san_name, clone_name
       
    2. Preserve Settings:
       - Clone settings are stored in Kodi's userdata folder (not the addon folder)
       - By deleting and recreating the addon folder, settings remain intact
       
    3. File Operations:
       - Delete the existing clone addon folder
       - Copy fresh files from main EasyTV installation
       - Remove service.py, clone.py (clones don't need these)
       - Replace addon.xml and settings.xml with clone versions
       - Update addon ID references in Python files to match clone ID
       
    4. Re-registration:
       - Disable and re-enable the addon via JSON-RPC
       - This ensures Kodi recognizes the updated files

Arguments (via sys.argv):
    1. src_path: Path to main EasyTV installation
    2. new_path: Path to clone addon folder
    3. san_name: Sanitized addon ID (e.g., script.easytv.kids)
    4. clone_name: Human-readable name (e.g., "Kids Shows")

Logging:
    Module: update_clone
    Events:
        - clone.update (INFO): Clone updated successfully
        - clone.update_fail (ERROR): Clone update failed
        - clone.register_fail (WARNING): Addon re-registration failed
"""

import shutil
import xbmc
import xbmcgui
import xbmcaddon
import sys
import os
from xml.etree import ElementTree as et
import fileinput

# Import shared utilities
# NOTE: This script is executed via RunScript() from default.py, which sets
# the working directory to the addon's resources/ folder. Therefore we use
# "from lib." instead of "from resources.lib." which is used elsewhere.
# See clone.py for contrast - it's imported as a module, not executed directly.
from lib.utils import lang, get_logger
from lib.constants import ADDON_ENABLE_DELAY_MS

src_path   = sys.argv[1]
new_path   = sys.argv[2]
san_name   = sys.argv[3]
clone_name = sys.argv[4]

__addon__        = xbmcaddon.Addon('script.easytv')
__addonid__      = __addon__.getAddonInfo('id')
__setting__      = __addon__.getSetting
dialog           = xbmcgui.Dialog()

log              = get_logger('update_clone')



def errorHandle(exception, trace, new_path=False):

    log.error("Clone update failed", event="clone.update_fail", error=str(exception), trace=str(trace))

    dialog.ok('EasyTV', lang(32148) + '\n' + lang(32141))
    if new_path:
        shutil.rmtree(new_path, ignore_errors=True)
    sys.exit()


def Main():
    try:
        # remove the existing clone (the settings will be saved in the userdata/addon folder)
        shutil.rmtree(new_path)


        # copy current addon to new location
        IGNORE_PATTERNS = ('.pyc','CVS','.git','tmp','.svn')
        shutil.copytree(src_path,new_path, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))

        # remove the unneeded files
        addon_file = os.path.join(new_path,'addon.xml')

        os.remove(os.path.join(new_path,'service.py'))
        os.remove(addon_file)
        os.remove(os.path.join(new_path,'resources','settings.xml'))
        os.remove(os.path.join(new_path,'resources','clone.py'))

        # replace the settings file and addon file with the truncated one
        shutil.move( os.path.join(new_path,'resources','addon_clone.xml') , addon_file )
        shutil.move( os.path.join(new_path,'resources','settings_clone.xml') , os.path.join(new_path,'resources','settings.xml') )

    except Exception as e:
        _, _, tb = sys.exc_info()  # Only need traceback
        errorHandle(e, tb, new_path)

    # edit the addon.xml to point to the right folder
    tree = et.parse(addon_file)
    root = tree.getroot()
    root.set('id', san_name)
    root.set('name', clone_name)
    tree.find('.//summary').text = clone_name
    tree.write(addon_file)



    # replace the id on these files, avoids Access Violation
    py_files = [os.path.join(new_path,'resources','selector.py') , os.path.join(new_path,'resources','playlists.py'),os.path.join(new_path,'resources','update_clone.py'),os.path.join(new_path,'resources','episode_exporter.py')]

    for py in py_files:
        try:
            for line in fileinput.input(py, inplace=True):
                print(line.replace('script.easytv', san_name), end='')
        finally:
            fileinput.close()

    # stop and start the addon to have it show in the Video Addons window
    try:
        log.debug("Toggling addon registration", addon_id=san_name)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s","enabled":false}}' % san_name)
        xbmc.sleep(ADDON_ENABLE_DELAY_MS)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s", "enabled":true}}' % san_name)
    except Exception:
        log.warning("Addon re-registration failed", event="clone.register_fail", addon_id=san_name)

    dialog.ok('EasyTV', lang(32149) + '\n' + lang(32147))

if __name__ == "__main__":

    log.info("Clone update started", event="clone.update_start", clone_name=clone_name)

    Main()

    log.info("Clone update completed", event="clone.update_complete", clone_name=clone_name)
