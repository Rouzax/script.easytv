# Clones

> **Configured under** **Settings → Advanced → Tools → Create EasyTV copy...**

Create multiple EasyTV instances with completely independent settings. Each clone is a separate addon that shares the core code but maintains its own configuration.

---

## Why Clone?

| Use Case | Main EasyTV | Clone |
|----------|-------------|-------|
| **Different content** | All shows | Only comedies |
| **Different modes** | Browse mode | Random playlist |
| **Different users** | Adult content | Kids-only content |
| **Different rooms** | Living room setup | Bedroom setup |

---

## Creating a Clone

1. Go to **Settings → Advanced → Tools**
2. Click **Create EasyTV copy...**
3. Enter a name for the clone (e.g., "Kids TV", "Comedies")
4. A progress dialog shows the creation steps
5. A prompt offers to restart Kodi (recommended)

### What Gets Created

A new addon appears in **Add-ons → Program add-ons**:

- Named "EasyTV - [Your Name]" (e.g., "EasyTV - Kids TV")
- Completely separate settings
- Uses the same background service data
- Can be added to your home screen independently

---

## Clone Settings

Each clone has its own:

- Launch behavior (Browse vs Random vs Ask)
- Show filter (which shows to include)
- Smart playlist selection
- Random-order shows list
- Browse mode appearance
- Random playlist configuration
- All playback settings

### Custom Icons for Clones

Each clone can have its own custom icon, making them visually distinct in Kodi menus:

1. Open the clone's settings
2. Go to **EasyTV > Appearance**
3. Click **Set custom icon**
4. Choose an image file

This makes it easy to identify different clones at a glance (e.g., a kids icon for a kids-only clone).

---

## Clone Limitations

Clones share:

- The core EasyTV code
- The background service's show/episode data
- Duration cache
- Auto-created smart playlists (managed by main addon only)

Clones do NOT:

- Affect each other's settings or the main addon's settings
- Participate in [multi-instance sync](multi-instance-sync.md). Clones use the main addon's local data only.
- Run their own background service. The main EasyTV addon handles all background work for every clone.

---

## Updating Clones

When you update EasyTV (install a new version), clones need to be updated too:

1. Launch a clone after updating the main addon
2. EasyTV detects the version mismatch
3. A dialog appears: "EasyTV has updated and this clone is now out of date"
4. Click **Yes** to update
5. A progress dialog shows the update steps
6. Restart Kodi when prompted

The update process:

- Preserves all clone settings
- Updates only the code files
- Takes just a few seconds

---

## Removing a Clone

1. Go to **Settings → Add-ons → My add-ons → Program add-ons**
2. Find the clone (e.g., "EasyTV - Kids TV")
3. Click **Uninstall**

This removes only the clone, not the main EasyTV addon.

---

## Power User Pattern: Main as Service, Clones as Entry Points

For advanced setups, you can use the main EasyTV addon purely as a background service manager while using clones as your actual entry points. This pattern is useful when you want different "channels" for different types of content.

**Example setup:**

| Addon | Purpose | Configuration |
|-------|---------|---------------|
| **Main EasyTV** | Background service only | Filters to master playlist, generates smart playlists, never launched directly |
| **EasyTV - In Progress** | Continue watching | Launches to Browse Mode, sorted by last watched |
| **EasyTV - Season Premiere** | New seasons | Filters to Season Premieres playlist |
| **EasyTV - Show Premiere** | New shows to start | Filters to Show Premieres playlist |

**Benefits:**

- Each clone can be added to your home screen as a separate menu item
- Different filters for different viewing moods
- Main addon handles all background work and smart playlist generation
- Smart playlists inherit the main addon's show filter (if enabled)

**Setup steps:**

1. Configure the main addon's show filter to your master playlist
2. Enable smart playlist export and "Apply show filter to smart playlists" on the main addon
3. Create clones for each "channel" you want
4. Configure each clone with its own filter or launch behavior
5. Add clones to your skin's home menu

---

## Related Pages

- **[Settings Reference](settings-reference.md):** All EasyTV settings
- **[Multi-Instance Sync](multi-instance-sync.md):** Why clones don't participate in sync
- **[Auto-Created Smart Playlists](auto-generated-playlists.md):** Apply show filter to smart playlists for the Power User Pattern
- **[Smart Playlist Integration](smart-playlist-integration.md):** Filter strategies that pair with clones
