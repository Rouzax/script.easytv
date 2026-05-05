# Advanced Features

EasyTV includes several advanced features for power users.

- **[Clones](clones.md):** Multiple EasyTV instances with independent settings.
- **[Episode Export](episode-export.md):** Copy your "next episode" files to another location.
- **[Auto-Generated Smart Playlists](auto-generated-playlists.md):** Smart playlists for skin widgets and channel surfing.

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
