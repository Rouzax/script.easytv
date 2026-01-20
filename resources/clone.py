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

    sanitized_suffix = sanitize_filename(clone_name)
    
    # Safeguard: if sanitization results in empty or non-alphanumeric string, use fallback
    # This handles edge cases like "!!!" (all special chars) or "..." (all dots)
    if not sanitized_suffix or not any(c.isalnum() for c in sanitized_suffix):
        sanitized_suffix = 'clone'
        log.warning("Clone name sanitized to invalid, using fallback", 
                   event="clone.name_fallback", original=clone_name)
    
    san_name = 'script.easytv.' + sanitized_suffix
    new_path = os.path.join(addon_path, san_name)
    
    # Get parent version to use for clone
    parent_version = __addon__.getAddonInfo('version')

    log.debug("Clone parameters", clone_name=clone_name, san_name=san_name, 
              new_path=new_path, script_path=scriptPath, parent_version=parent_version)

    # Safeguard: prevent overwriting parent addon
    if san_name == __addonid__:
        log.error("Invalid clone name would overwrite parent", 
                 event="clone.invalid_name", san_name=san_name)
        dialog.ok('EasyTV', lang(32145))  # "Name already in use"
        __addon__.openSettings()
        sys.exit()

    #check if folder exists, if it does then abort
    if os.path.isdir(new_path):

        log.warning("Clone name already in use", event="clone.duplicate", name=san_name)

        dialog.ok('EasyTV',lang(32145))
        __addon__.openSettings()
        sys.exit()

    # Use Kodi's temp folder to build clone before moving to addons
    # This prevents Kodi from caching incomplete/incorrect files
    temp_base = xbmcvfs.translatePath('special://temp/')
    temp_path = os.path.join(temp_base, f'easytv_clone_{san_name}')
    
    try:
        # Clean up any leftover temp folder
        if os.path.isdir(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)

        # copy current addon to temp location first
        IGNORE_PATTERNS = ('.pyc','CVS','.git','tmp','.svn','__pycache__')
        shutil.copytree(scriptPath, temp_path, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))


        # remove the unneeded files
        addon_file = os.path.join(temp_path,'addon.xml')

        os.remove(os.path.join(temp_path,'service.py'))
        os.remove(addon_file)
        #os.remove(os.path.join(temp_path,'resources','selector.py'))
        os.remove(os.path.join(temp_path,'resources','settings.xml'))
        os.remove(os.path.join(temp_path,'resources','clone.py'))

        # replace the settings file and addon file with the truncated one
        shutil.move( os.path.join(temp_path,'resources','addon_clone.xml') , addon_file )
        shutil.move( os.path.join(temp_path,'resources','settings_clone.xml') , os.path.join(temp_path,'resources','settings.xml') )

        # Update section id in settings.xml to match clone addon id
        # Without this, Kodi can't match settings to the clone addon
        settings_file = os.path.join(temp_path, 'resources', 'settings.xml')
        for line in fileinput.input(settings_file, inplace=True):
            print(line.replace('section id="script.easytv"', f'section id="{san_name}"'), end='')
        fileinput.close()

        # Update strings.po header in ALL language folders to match clone addon id
        # Without this, Kodi 21+ won't load language strings for the clone
        # This handles future Weblate translations (multiple language folders)
        language_dir = os.path.join(temp_path, 'resources', 'language')
        for lang_folder in os.listdir(language_dir):
            strings_file = os.path.join(language_dir, lang_folder, 'strings.po')
            if os.path.isfile(strings_file):
                for line in fileinput.input(strings_file, inplace=True):
                    line = line.replace('# Addon Name: EasyTV', f'# Addon Name: {clone_name}')
                    line = line.replace('# Addon id: script.easytv', f'# Addon id: {san_name}')
                    print(line, end='')
                fileinput.close()

        # edit the addon.xml to set clone id, name, and version
        tree = et.parse(addon_file)
        root = tree.getroot()
        root.set('id', san_name)
        root.set('name', clone_name)
        root.set('version', parent_version)  # Clone inherits parent version
        tree.find('.//summary').text = clone_name
        tree.write(addon_file)

        # replace the id on these files, avoids Access Violation
        py_files = [
            os.path.join(temp_path,'resources','selector.py'),
            os.path.join(temp_path,'resources','playlists.py'),
            os.path.join(temp_path,'resources','update_clone.py'),
            os.path.join(temp_path,'resources','episode_exporter.py')
        ]

        for py in py_files:
            for line in fileinput.input(py, inplace=True):
                print(line.replace('script.easytv', san_name), end='')
            fileinput.close()

        # All modifications complete - now move from temp to final location
        # This ensures Kodi sees a fully-prepared addon with correct strings.po
        shutil.move(temp_path, new_path)

    except Exception as e:
        _, _, tb = sys.exc_info()  # Only need traceback
        # Clean up temp folder on error
        if os.path.isdir(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)
        errorHandle(e, tb, new_path)

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
        
        # Give Kodi time to fully enable the addon
        xbmc.sleep(1000)
            
    except Exception:
        pass  # Silently ignore - addon will still work after Kodi restart

    log.info("Clone created successfully", event="clone.create", name=clone_name, 
             addon_id=san_name, version=parent_version)

    # Inform user that restart is needed for labels
    # Note: RestartApp doesn't work reliably on Windows (quits but doesn't relaunch)
    # So we just inform the user and let them restart when convenient
    dialog.ok('EasyTV', lang(32146) + '\n' + lang(32147))


if __name__ == "__main__":

    log.info("Clone creation started", event="clone.start")

    Main()

    log.info("Clone creation completed", event="clone.complete")
