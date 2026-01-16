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
EasyTV Clone Creation

This module creates independent "clones" of EasyTV that allow users to have
multiple Home menu items, each with their own separate settings.

Clone Lifecycle:
    1. Creation:
       - User triggers via "Create Clone" in EasyTV settings
       - Dialog prompts for a name (e.g., "Kids Shows", "Night Mode")
       - A new addon folder is created: script.easytv.<sanitized_name>
       
    2. File Structure:
       - Copies entire EasyTV addon to new location
       - Removes service.py (clones don't run background services)
       - Removes clone.py (clones can't create sub-clones)
       - Replaces addon.xml and settings.xml with clone-specific versions
       - Updates Python files to reference the new addon ID
       
    3. Registration:
       - Disables and re-enables the new addon to register with Kodi
       - Clone appears in Video Addons with the user's chosen name
       
    4. Usage:
       - Each clone has independent settings (stored in userdata)
       - All clones share the same background service from main EasyTV
       - Clones can be updated when main EasyTV updates (via update_clone.py)
       - Clones can be removed by uninstalling from Kodi addon manager

Note: Settings are stored in Kodi's userdata folder per-addon, so clones
maintain their settings independently even after updates.

Logging:
    Module: clone
    Events:
        - clone.create (INFO): Clone created successfully
        - clone.fail (ERROR): Clone creation failed
        - clone.register_fail (WARNING): Addon re-registration failed
"""

import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import sys
import shutil
from xml.etree import ElementTree as et
import fileinput

# Import shared utilities
from resources.lib.utils import lang, get_logger, sanitize_filename
from resources.lib.constants import ADDON_ENABLE_DELAY_MS


__addon__        = xbmcaddon.Addon('script.easytv')
__addonid__      = __addon__.getAddonInfo('id')
__setting__      = __addon__.getSetting
dialog           = xbmcgui.Dialog()
scriptPath       = __addon__.getAddonInfo('path')
addon_path       = xbmcvfs.translatePath('special://home/addons')
log              = get_logger('clone')


def errorHandle(exception, trace, new_path=False):

    log.error("Clone creation failed", event="clone.fail", error=str(exception), trace=str(trace))

    dialog.ok('EasyTV', lang(32140) + '\n' + lang(32141))
    if new_path:
        shutil.rmtree(new_path, ignore_errors=True)
    sys.exit()


def Main():
    first_q = dialog.yesno('EasyTV', lang(32142) + '\n' + lang(32143) + '\n' + lang(32144))
    if first_q != 1:
        sys.exit()
    else:
        keyboard = xbmc.Keyboard(lang(32139))
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            clone_name = keyboard.getText()
        else:
            sys.exit()

    # if the clone_name is blank then use default name of 'Clone'
    if not clone_name:
        clone_name = 'Clone'

    san_name = 'script.easytv.' + sanitize_filename(clone_name)
    new_path = os.path.join(addon_path, san_name)

    log.debug("Clone parameters", clone_name=clone_name, san_name=san_name, 
              new_path=new_path, script_path=scriptPath)

    #check if folder exists, if it does then abort
    if os.path.isdir(new_path):

        log.warning("Clone name already in use", event="clone.duplicate", name=san_name)

        dialog.ok('EasyTV',lang(32145))
        __addon__.openSettings()
        sys.exit()

    try:

        # copy current addon to new location
        IGNORE_PATTERNS = ('.pyc','CVS','.git','tmp','.svn')
        shutil.copytree(scriptPath,new_path, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))


        # remove the unneeded files
        addon_file = os.path.join(new_path,'addon.xml')

        os.remove(os.path.join(new_path,'service.py'))
        os.remove(addon_file)
        #os.remove(os.path.join(new_path,'resources','selector.py'))
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

    # Notify Kodi to scan for new addons, then enable the clone
    try:
        # First, tell Kodi to rescan the addons directory
        xbmc.executebuiltin('UpdateLocalAddons')
        # Give Kodi time to fully scan - this can take a few seconds on large libraries
        xbmc.sleep(3000)
        
        # Now enable the newly discovered addon
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s","enabled":false}}' % san_name)
        xbmc.sleep(ADDON_ENABLE_DELAY_MS)
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s", "enabled":true}}' % san_name)
    except Exception:
        pass  # Silently ignore - addon will still work after Kodi restart

    log.info("Clone created successfully", event="clone.create", name=clone_name, addon_id=san_name)

    dialog.ok('EasyTV', lang(32146) + '\n' + lang(32147))


if __name__ == "__main__":

    log.info("Clone creation started", event="clone.start")

    Main()

    log.info("Clone creation completed", event="clone.complete")
