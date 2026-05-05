# Troubleshooting & FAQ

Common issues, solutions, and frequently asked questions about EasyTV.

---

## Common Issues

### "EasyTV Service is not running"

The background service must be running for EasyTV to work.

**Solution:**
1. Go to **Settings → Add-ons → My add-ons → Services**
2. Find **EasyTV** in the list
3. Ensure it shows as **Enabled**
4. If disabled, click to enable
5. Restart Kodi

**If still not working:**
- Check Kodi's log for service startup errors
- Ensure EasyTV is properly installed (not just extracted)
- Try reinstalling from the zip file

---

### Empty Episode List

The browse list shows no shows.

**Possible causes and solutions:**

| Cause | Solution |
|-------|----------|
| Service still scanning | Wait for "Database analysis complete" notification |
| No unwatched episodes | Add some unwatched content to your library |
| Show filter too restrictive | Disable "Use only selected shows" or select more shows |
| Duration filter excluding all | Disable duration filter or widen the range |
| Smart playlist has no matches | Check your playlist rules in Kodi |

**Quick test:**
1. Go to Settings → Shows → Show Filter
2. Disable "Use only selected shows"
3. Go to Settings → Shows → Episode Duration
4. Disable "Enable duration filter"
5. Refresh the episode list

---

### "EasyTV is still populating with shows"

The service hasn't finished its initial scan.

**Solution:** Wait for the scan to complete. A notification appears when ready.

**Taking too long?**
- First run calculates episode durations (one-time cost)
- Large libraries on slow storage take longer
- Network-attached libraries are slower than local
- Check that Kodi isn't doing a library update simultaneously

---

### Episodes Not Marking as Watched

Episodes you watch don't update in EasyTV.

**Check Kodi settings:**
1. Go to **Settings → Player → Videos**
2. Find "Minimum percentage watched" (default 90%)
3. Ensure you're watching past this threshold

**Check library updates:**
- Verify your library is updating properly
- Try a manual library update: **Context menu → Update Library**

**Check playback source:**
- Playback must be from your Kodi library (not external sources)
- Streaming addons may not update library status

---

### Wrong Episode Shown

EasyTV suggests an episode you've already watched, or skips one you haven't.

**Possible causes:**

| Cause | Solution |
|-------|----------|
| Watch status incorrect in Kodi | Manually correct via Kodi's library |
| Episode numbering mismatch | Verify your files match Kodi's database |
| Multiple versions of same episode | Remove duplicates from library |
| iStream or streaming content | These may not report watch status correctly |

**To verify:**
1. Open the show in Kodi's library (not EasyTV)
2. Check episode watch status
3. Manually mark episodes watched/unwatched as needed
4. Refresh EasyTV's list

---

### Random Playlist Has No Content

Playlist generation finds nothing to add.

**Check these settings:**

| Setting | Issue | Solution |
|---------|-------|----------|
| Playlist content | Set to wrong type | Match your content (TV, movies, or both) |
| Episode selection | "Unwatched only" but all watched | Change to "Both" or "Watched" |
| Movie selection | Same issue for movies | Adjust selection setting |
| Show filter | Too restrictive | Widen filter or disable |
| Smart playlist | No matches | Edit playlist rules |
| Duration filter | Excluding all shows | Disable or adjust range |

---

### Slow Performance

EasyTV is sluggish on your device.

**For Browse Mode:**
1. Enable **Settings → Browse Mode → Performance → Limit shows displayed**
2. Set **Maximum shows** to 10-15
3. Use **Card List** view style. Posters, Big Screen, Split View, and Showcase pull and render more artwork per item.

**For Random Playlist:**
- Playlist building takes a few seconds. This is normal.
- Larger libraries take longer
- Partial prioritization adds some overhead

**General tips:**
- Ensure your Kodi library is well-maintained
- Remove duplicate entries
- Consider local storage vs network for better speeds

---

### Clone Won't Update

After updating EasyTV, a clone still shows old behavior.

**Solution:**
1. Launch the clone
2. Accept the update prompt when it appears
3. A progress dialog shows the update steps
4. Restart Kodi when prompted

**If no prompt appears:**
- The clone may already be updated
- Try uninstalling and recreating the clone

---

### Smart Playlist Not Working

EasyTV doesn't seem to filter by your smart playlist.

**Verify playlist location:**
- Must be in `special://profile/playlists/video/`
- File extension must be `.xsp`

**Verify playlist type:**
- TV show filter requires `type="tvshows"`
- Movie filter requires `type="movies"`

**Test in Kodi:**
1. Go to **Videos → Playlists**
2. Open your playlist
3. Verify it shows expected content
4. If empty in Kodi, the rules need adjustment

---

### Duration Filter Not Working

Shows outside your duration range still appear.

**Possible causes:**

| Cause | Solution |
|-------|----------|
| Duration data not cached | Wait for service to complete analysis |
| Show has no stream metadata | These shows are excluded when filter is active |
| Invalid settings (min > max) | EasyTV warns and disables filter |
| Filter was just changed | Refresh the list or restart service |

**Note:** Duration is calculated from video file stream metadata. Shows without this data (some streaming sources) will have duration=0 and be excluded when filtering.

---

### Multi-Instance Sync Issues

If you're using [multi-instance sync](multi-instance-sync.md), these are the most common problems.

#### Database Unavailable

**Symptoms:** Log shows `Using window property storage` instead of `Using shared database storage`. Sync is silently inactive.

**Solutions:**
1. Verify Kodi can access the shared database (your library loads normally)
2. Check `advancedsettings.xml` has `<videodatabase>` with `<type>mysql</type>`
3. Ensure `script.module.pymysql` addon is installed
4. Check the database server is running and reachable from this device

#### Devices Not Syncing

**Symptoms:** You watch on one device but the other still shows the old next episode.

**Solutions:**
1. Confirm multi-instance sync is enabled on **all** devices
2. Verify all devices connect to the **same** database server and database name
3. Check logs on each device. Look for `Using shared database storage`.
4. Ensure random-order shows and positioned specials settings match across devices

#### pymysql Missing

**Symptoms:** A dialog appears saying "pymysql not available" and sync disables itself.

**Solution:** Install `script.module.pymysql` from the Kodi addon repository. It's normally installed as an EasyTV dependency, but may be missing if you installed EasyTV manually.

---

## Debug Logging

For diagnosing complex issues, enable detailed logging.

### Enabling Logs

1. Go to **Settings → Advanced → Debugging**
2. Enable **Enable debug logging**
3. Reproduce the issue
4. Check the log file

### Log File Locations

| Platform | Path |
|----------|------|
| **Windows** | `%APPDATA%\Kodi\userdata\addon_data\script.easytv\logs\easytv.log` |
| **Linux** | `~/.kodi/userdata/addon_data/script.easytv/logs/easytv.log` |
| **macOS** | `~/Library/Application Support/Kodi/userdata/addon_data/script.easytv/logs/easytv.log` |
| **LibreELEC** | `/storage/.kodi/userdata/addon_data/script.easytv/logs/easytv.log` |
| **OSMC** | `/home/osmc/.kodi/userdata/addon_data/script.easytv/logs/easytv.log` |

### What to Look For

- **ERROR** entries indicate failures
- **WARNING** entries indicate recoverable issues
- Timestamps help correlate with when problems occurred
- Module names (service, data, playback, ui) indicate where issues happen

### Reporting Bugs

When reporting issues:
1. Enable debug logging
2. Reproduce the issue
3. Copy relevant log sections
4. Include:
   - What you expected to happen
   - What actually happened
   - Your EasyTV version
   - Your Kodi version
   - Relevant log entries

---

## Frequently Asked Questions

### General

**Q: Does EasyTV work with Kodi 20?**
A: No. EasyTV requires Kodi 21 (Omega) or later.

**Q: Does EasyTV modify my library?**
A: No. EasyTV only reads from your library. It never modifies shows, episodes, or watch status except through normal Kodi playback.

**Q: Can I use EasyTV with multiple profiles?**
A: Yes. Each Kodi profile has separate EasyTV settings and data.

**Q: Does EasyTV work with streaming addons?**
A: Partially. EasyTV tracks library content. Streaming addons may not update library watch status, so tracking may be incomplete.

**Q: Can I use EasyTV on multiple Kodi devices?**
A: Yes! With [multi-instance sync](multi-instance-sync.md), your watch progress stays in sync across all devices. Requires a shared MySQL/MariaDB video database.

**Q: What are "positioned specials"?**
A: Some shows have specials that belong between specific episodes (TVDB provides this positioning data). When enabled in Settings → Shows, these specials appear at their correct position in the watch order instead of being excluded.

---

### Browse Mode

**Q: Why don't I see all my shows?**
A: Check your show filter, duration filter, and premiere settings. EasyTV only shows what matches your criteria.

**Q: Can I manually pick any episode, not just the "next" one?**
A: EasyTV is designed for "next episode" tracking. For browsing all episodes, use Kodi's normal library interface.

**Q: Why does the same show appear at a different position after watching?**
A: If you're sorted by "Last Watched," shows move to the top when you watch them.

---

### Random Playlist

**Q: Why does playlist building take several seconds?**
A: EasyTV queries your library, calculates candidates, checks for partials, and builds the playlist. This is normal for larger libraries.

**Q: Can I skip to the next item in a playlist?**
A: Yes, use Kodi's normal skip controls or the playlist window.

**Q: Why do I see the same show multiple times?**
A: "Allow multiple episodes of same TV Show" is enabled. Disable it for variety.

**Q: What's the maximum playlist length?**
A: 50 items. For longer viewing sessions, use Playlist Continuation.

---

### Content Filtering

**Q: How do I only watch comedies?**
A: Create a smart playlist filtering Genre = Comedy, then use it as EasyTV's show filter.

**Q: Can I exclude specific shows?**
A: Yes. Create a smart playlist with exclusion rules, or use manual show selection and don't select those shows.

**Q: How does duration filtering work with multi-episode files?**
A: Duration is calculated per-show (median of sample episodes), not per-file. Multi-episode files may report combined duration.

---

### Random-Order Shows

**Q: What happens when all episodes are watched?**
A: For "Unwatched only" selection, the show has no candidates. For "Both," watched episodes can still be picked.

**Q: Can I have different random-order settings in clones?**
A: Yes! Each clone has its own random-order show list.

---

### Movies

**Q: Can I use EasyTV for movies only?**
A: Yes. Set Playlist content to "Movies only" for movie-exclusive random playlists. Browse Mode is TV-only.

**Q: Why aren't my movies appearing in playlists?**
A: Check Movie selection setting, verify you have movies matching your filter, and ensure Playlist content includes movies.

---

### Technical

**Q: How much storage does EasyTV use?**
A: Minimal. The duration cache and settings file are typically under 1MB combined.

**Q: Does EasyTV run all the time?**
A: The background service runs continuously (like all Kodi services) but uses minimal resources when idle.

**Q: Can I backup my EasyTV settings?**
A: Yes. Copy the `addon_data/script.easytv/` folder from your Kodi userdata directory.

---

## Getting Help

### Resources

| Resource | Link |
|----------|------|
| **GitHub Issues** | [Report a bug](https://github.com/Rouzax/script.easytv/issues) |
| **Kodi Forum** | [EasyTV Thread](https://forum.kodi.tv/showthread.php?tid=383902) |
| **Documentation** | You're here! |

### When Asking for Help

Include:
1. EasyTV version (from addon info)
2. Kodi version (from System → System info)
3. What you're trying to do
4. What's happening instead
5. Relevant settings
6. Log excerpts (if applicable)

---

## Related Pages

- **[Installation](installation.md):** Initial setup
- **[Settings Reference](settings-reference.md):** All settings explained
- **[Smart Playlist Integration](smart-playlist-integration.md):** Filtering troubleshooting
- **[Multi-Instance Sync](multi-instance-sync.md):** Sync setup and recovery
