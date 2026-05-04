# Migration Guide

Upgrade notes and breaking changes for major EasyTV releases. Check this page when updating to ensure a smooth transition.

---

## v1.4.0: Positioned Specials

*Released: 2026-02*

### What's New

**Positioned specials support:** Some shows (like SpongeBob SquarePants) have specials that are plot-relevant and should be watched between specific episodes. TVDB provides positioning data for these specials, and Kodi stores it in episode metadata. EasyTV can now include these positioned specials in the watch order.

### Action Required

**None.** This is an opt-in feature with no breaking changes.

### Optional Setup

To enable positioned specials:
1. Go to **Settings → Shows → Show Filter**
2. Enable **Include positioned specials in watch order**
3. Default is **Off** (existing behavior preserved)

> **Multi-instance sync users:** If you enable this setting, enable it on **all** devices sharing the same database. Different settings will cause devices to disagree on the next episode.

### Bug Fixes Worth Noting

- Silent service crash during overnight library scans with multi-instance sync is now fixed (v1.4.0-alpha2). If you experienced the service stopping after idle periods, this update resolves it.
- Batch write performance improved significantly for large libraries with sync enabled.

---

## v1.3.0: Multi-Instance Sync

*Released: 2026-01*

### What's New

**Multi-instance sync:** Share watch progress across multiple Kodi devices using a shared MySQL/MariaDB database. See [Multi-Instance Sync](multi-instance-sync.md) for full documentation.

### Action Required

**None.** Sync is disabled by default. Your existing single-device setup continues to work unchanged.

### Optional Setup

If you have multiple Kodi devices with a shared MySQL/MariaDB video database:
1. Go to **Settings → Advanced → Multi-Instance Sync**
2. Enable **Multi-instance sync**
3. Repeat on each device
4. See [Multi-Instance Sync](multi-instance-sync.md) for detailed setup instructions

### Requirements for Sync

- Shared MySQL/MariaDB video database (configured in `advancedsettings.xml`)
- `script.module.pymysql` addon (bundled with EasyTV)
- EasyTV v1.3.0+ on all devices

---

## v1.2.4: Smart Playlist Overhaul

*Released: 2026-01-25*

### What's New

- **TVShow smart playlists:** Browse your next episodes by show (great for skin widgets)
- **Show Premieres / Season Premieres:** Two new playlist categories
- **Show filter for playlists:** Apply your show filter to auto-created playlists

### Breaking Change: Playlist Filenames

Smart playlist filenames have changed. **If you have skin widgets or menu entries pointing to EasyTV playlists, you must update them.**

| Old Filename | New Filename |
|-------------|-------------|
| `EasyTV - All Shows.xsp` | `EasyTV - Episode - All Shows.xsp` |
| `EasyTV - Continue Watching.xsp` | `EasyTV - Episode - Continue Watching.xsp` |
| `EasyTV - Start Fresh.xsp` | `EasyTV - Episode - Start Fresh.xsp` |

Old playlist files are automatically deleted on upgrade. Settings migrate automatically.

### Action Required

**Only if you use EasyTV playlists in skin widgets or PseudoTV Live:**

1. Open your skin settings or PseudoTV Live configuration
2. Find any references to old EasyTV playlist filenames
3. Update them to the new filenames (see table above)
4. If using TVShow playlists for widgets, configure those separately (they are a new feature)

**If you don't use auto-created playlists**, no action is needed.

### New Playlist Categories

Two new Episode and TVShow playlist variants were added:

| Category | Contents |
|----------|----------|
| **Show Premieres** | Shows at S01E01 (brand new shows to discover) |
| **Season Premieres** | Shows at S02E01+ (new seasons of shows you've watched) |

---

## General Upgrade Notes

### Updating EasyTV

1. Download the new version from [GitHub Releases](https://github.com/Rouzax/script.easytv/releases)
2. Install via **Settings → Add-ons → Install from zip file**
3. Restart Kodi (recommended after major version updates)

### Updating Clones

After updating the main addon, each clone needs updating:
1. Launch the clone
2. Accept the update prompt
3. A progress dialog shows the update steps
4. Restart Kodi when prompted

### Settings Compatibility

EasyTV maintains settings compatibility within major versions (1.x.x). New settings always have sensible defaults for existing users. You should never lose your configuration during a minor version update.

---

## Related Pages

- **[Installation](installation.md):** Fresh installation guide
- **[Multi-Instance Sync](multi-instance-sync.md):** Full sync documentation
- **[Advanced Features](advanced-features.md):** Clone management, smart playlists
- **[Settings Reference](settings-reference.md):** All settings explained
