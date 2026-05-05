# Advanced Features

EasyTV includes several advanced features for power users.

- **[Clones](clones.md):** Multiple EasyTV instances with independent settings.
- **[Episode Exporter](#episode-exporter):** Copy your "next episode" files to another location.
- **[Auto-Created Smart Playlists](#auto-created-smart-playlists):** Smart playlists for skin widgets and channel surfing.

---

## Episode Exporter

Copy your "next episode" files to another location. Perfect for offline viewing on trips, transferring to a portable device, or backup.

### How It Works

1. Select episodes in Browse Mode
2. Choose export location
3. EasyTV copies the video files

### Using the Exporter

#### From Browse Mode

1. Open Browse Mode (episode list)
2. Enable **Multi-Select** from the context menu
3. Select the episodes you want to export
4. Open context menu → **Export Selection**
5. Choose a destination folder
6. Files are copied

#### From Settings

1. Go to **Settings → Advanced → Tools**
2. Click **Export episodes to folder...**
3. This exports ALL current next episodes (one per show)

### Export Details

- Copies the actual video files (not shortcuts)
- Preserves original filenames
- Shows progress during transfer
- Reports any failures at the end

### Use Cases

| Scenario | Workflow |
|----------|----------|
| **Trip preparation** | Export a few episodes from multiple shows |
| **Device transfer** | Export to USB drive, copy to tablet |
| **Backup** | Periodically export next episodes to NAS |
| **Sharing** | Export specific episodes for someone |

### Limitations

- Only exports video files, not subtitles or extras
- Large files take time to copy
- Destination needs enough free space
- Network destinations may be slow

---

## Auto-Created Smart Playlists

> **Upgraded from v1.2.3 or earlier?** Playlist filenames changed in v1.2.4. If your skin widgets or PseudoTV Live channels reference old EasyTV playlist names, see the [Migration Guide](migration-guide.md#v124-smart-playlist-overhaul) for the filename mapping.

EasyTV can automatically maintain smart playlists for use by other addons or skin widgets. There are two types of playlists: **Episode playlists** for channel surfing and **TVShow playlists** for skin widgets.

### Enabling Auto-Playlists

1. Go to **Settings → Advanced → Background Service**
2. Enable **Export Episode smart playlists** for channel surfing playlists
3. Enable **Export TVShow smart playlists** for skin widget playlists

You can enable one or both depending on your needs.

### Episode vs TVShow Playlists

EasyTV creates two parallel sets of playlists with the same categories but different purposes:

| Type | Use Case | Ordering | Shows... |
|------|----------|----------|----------|
| **Episode** | Channel surfing, random playback | Random | The specific episode file to play |
| **TVShow** | Skin widgets, browsing | Alphabetical by title | The show itself (navigate to episode from there) |

**Episode playlists** are ideal when you want Kodi to play content directly. Each entry points to a specific episode file.

**TVShow playlists** are ideal for home screen widgets where you want to browse shows visually. Each entry is a TV show, and selecting it takes you to that show's page where you can see the next episode.

### Created Playlists

#### Episode Playlists

| Playlist | Filename | Contents |
|----------|----------|----------|
| **All Shows** | `EasyTV - Episode - All Shows.xsp` | Every show with an on-deck episode |
| **Continue Watching** | `EasyTV - Episode - Continue Watching.xsp` | Shows mid-season (episode 2+) |
| **Start Fresh** | `EasyTV - Episode - Start Fresh.xsp` | Shows at season start (episode 1) |
| **Show Premieres** | `EasyTV - Episode - Show Premieres.xsp` | Shows at S01E01 (brand new shows) |
| **Season Premieres** | `EasyTV - Episode - Season Premieres.xsp` | Shows at S02E01+ (new season of existing show) |

#### TVShow Playlists

| Playlist | Filename | Contents |
|----------|----------|----------|
| **All Shows** | `EasyTV - TVShow - All Shows.xsp` | Every show with an on-deck episode |
| **Continue Watching** | `EasyTV - TVShow - Continue Watching.xsp` | Shows mid-season (episode 2+) |
| **Start Fresh** | `EasyTV - TVShow - Start Fresh.xsp` | Shows at season start (episode 1) |
| **Show Premieres** | `EasyTV - TVShow - Show Premieres.xsp` | Shows at S01E01 (brand new shows) |
| **Season Premieres** | `EasyTV - TVShow - Season Premieres.xsp` | Shows at S02E01+ (new season of existing show) |

### Location

Playlists are created in:
```
special://profile/playlists/video/
```

### Filtering Playlists by Show Selection

If you use a show filter (Settings → Shows → Show Filter), you can apply that same filter to your auto-created playlists:

1. Go to **Settings → Advanced → Background Service**
2. Enable **Apply show filter to smart playlists**

When enabled, only shows matching your TV show playlist filter will appear in the generated smart playlists. This is useful when you want your skin widgets to show the same filtered content as your EasyTV experience.

**Important:** This setting only works on the **main EasyTV addon**, not on clones. Clones don't maintain smart playlists. They rely on the main addon's background service for playlist generation. If you want filtered playlists, configure the filter and this setting on the main addon.

### How Categorization Works

Shows are categorized by their **next episode**:

| Next Episode | Playlists |
|--------------|-----------|
| S01E01 | All Shows, Start Fresh, **Show Premieres** |
| S02E01, S03E01... | All Shows, Start Fresh, **Season Premieres** |
| S01E02, S01E03, S02E05... | All Shows, **Continue Watching** |

The premiere playlists help you find:
- **Show Premieres:** Brand new shows you haven't started yet
- **Season Premieres:** New seasons of shows you've already watched

### Automatic Updates

As you watch, shows move between playlists:

```
You're at S01E01 → All Shows + Start Fresh + Show Premieres
        ↓ (watch S01E01)
You're at S01E02 → All Shows + Continue Watching
        ↓ (watch all of season 1)
You're at S02E01 → All Shows + Start Fresh + Season Premieres
        ↓ (watch S02E01)
You're at S02E02 → All Shows + Continue Watching
        ↓ (finish the series)
No more episodes → Removed from all playlists
```

### Using with Skin Widgets

Most Kodi skins support widgets on the home screen. For the best experience:

1. Enable **Export TVShow smart playlists** in EasyTV settings
2. Configure your skin's widget to use an EasyTV TVShow playlist as its source
3. Choose the category that fits your widget's purpose:
   - **Continue Watching:** Shows you're in the middle of
   - **Start Fresh:** Shows ready to start a new season
   - **Show Premieres:** Brand new shows to discover
   - **Season Premieres:** New seasons waiting for you
   - **All Shows:** Everything EasyTV is tracking

TVShow playlists display show artwork and metadata, making them ideal for visual widgets.

### Using with PseudoTV Live

If you use PseudoTV Live for virtual TV channels:
1. Enable **Export Episode smart playlists** in EasyTV settings
2. Create a channel from an EasyTV Episode playlist
3. The channel automatically has your tracked episodes

Episode playlists work better here because they point directly to playable episode files.

### Using in Other Smart Playlists

You can use EasyTV playlists as criteria in your own smart playlists:
- Create a playlist with rule: "Playlist is EasyTV - Episode - Continue Watching"
- Combine with other rules (genre, year, etc.)

### Playlist XML Structure

Episode playlists identify content by filename:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<smartplaylist type="episodes">
    <name>EasyTV - Episode - All Shows</name>
    <match>one</match>
    <!--42--><rule field="filename" operator="is"><value>Breaking.Bad.S02E06.mkv</value></rule>
    <!--156--><rule field="filename" operator="is"><value>The.Office.S04E02.mkv</value></rule>
</smartplaylist>
```

TVShow playlists identify content by show title:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<smartplaylist type="tvshows">
    <name>EasyTV - TVShow - Continue Watching</name>
    <match>one</match>
    <!--42--><rule field="title" operator="is"><value>Breaking Bad</value></rule>
    <!--156--><rule field="title" operator="is"><value>The Office</value></rule>
    <order direction="ascending">sorttitle</order>
</smartplaylist>
```

Each entry has a comment with the show's numeric ID for internal tracking.

### Plugin Content Support

EasyTV's auto-playlists work with plugin-based libraries like **Jellyfin**, **Emby**, and **Plex**. For plugin content, the full plugin URL is used instead of a simple filename:

```xml
<!--42--><rule field="filename" operator="is"><value>plugin://plugin.video.jellyfin/...</value></rule>
```

This happens automatically. No configuration needed.

### Special Characters

Filenames with special characters (`&`, `<`, `>`) are automatically escaped to ensure valid XML:

```xml
<!-- "Pam & Tommy" becomes: -->
<value>Pam &amp; Tommy.S01E05.mkv</value>
```

### Performance Note

When enabled, EasyTV updates these playlists whenever episode tracking changes:
- After you watch something
- After library updates
- After service startup

The writes are batched for efficiency, but if you have a very large library, you may want to keep this disabled unless actively using the playlists.

---

## Debug Logging

For troubleshooting issues, EasyTV can write detailed logs.

### Enabling Debug Logging

1. Go to **Settings → Advanced → Debugging**
2. Enable **Enable debug logging**

### Log Location

EasyTV writes to a **separate log file** (not Kodi's main log):

| Platform | Path |
|----------|------|
| **Windows** | `%APPDATA%\Kodi\userdata\addon_data\script.easytv\logs\easytv.log` |
| **Linux** | `~/.kodi/userdata/addon_data/script.easytv/logs/easytv.log` |
| **macOS** | `~/Library/Application Support/Kodi/userdata/addon_data/script.easytv/logs/easytv.log` |
| **LibreELEC** | `/storage/.kodi/userdata/addon_data/script.easytv/logs/easytv.log` |
| **OSMC** | `/home/osmc/.kodi/userdata/addon_data/script.easytv/logs/easytv.log` |

### What Gets Logged

| Level | Content | Always Logged |
|-------|---------|---------------|
| **ERROR** | Operation failures, exceptions | Yes (Kodi + EasyTV log) |
| **WARNING** | Recoverable issues | Yes (Kodi + EasyTV log) |
| **INFO** | Lifecycle events (start, stop) | Yes (Kodi + EasyTV log) |
| **DEBUG** | Detailed diagnostics | Only when debug enabled (EasyTV log only) |

### Using Logs for Troubleshooting

1. Enable debug logging
2. Reproduce the issue
3. Open the log file
4. Look for ERROR or WARNING entries near the time of the issue
5. Share relevant log sections when reporting bugs

### Log Format

```
2025-01-21 12:34:56 [EasyTV.service] INFO: Service started, version=1.2.0
2025-01-21 12:34:57 [EasyTV.data] DEBUG: Fetching shows, count=47
2025-01-21 12:34:58 [EasyTV.playback] INFO: Playlist created, items=5
```

Each line includes:
- Timestamp
- Module (service, data, playback, ui)
- Level (INFO, DEBUG, WARNING, ERROR)
- Message with structured data

---

## Keyboard Shortcuts Summary

| Key | Context | Action |
|-----|---------|--------|
| **Enter** | Browse Mode | Play selected episode |
| **C** | Anywhere | Open context menu |
| **Backspace** | Browse Mode | Close EasyTV |
| **Esc** | Browse Mode | Close EasyTV |

---

## Related Pages

- **[Installation](installation.md):** Initial setup
- **[Settings Reference](settings-reference.md):** All settings explained
- **[Multi-Instance Sync](multi-instance-sync.md):** Share progress across devices
- **[Troubleshooting](troubleshooting-and-faq.md):** Common issues
- **[Smart Playlist Integration](smart-playlist-integration.md):** Using playlists for filtering
- **[Migration Guide](migration-guide.md):** Upgrade notes and breaking changes
