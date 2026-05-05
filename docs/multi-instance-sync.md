# Multi-Instance Sync

> **Configured under** **Settings → Advanced → Multi-Instance Sync → Enable multi-instance sync**

Share your watch progress across multiple Kodi devices. When you watch Episode 5 on one device, all other devices know to queue Episode 6.

---

## Overview

By default, EasyTV tracks your shows independently on each Kodi device. If you have Kodi in your living room and bedroom, they maintain separate "next episode" lists.

With multi-instance sync enabled, all your Kodi instances share a single database of watch progress. Watch something in one room and pick up right where you left off in another.

### When You'd Want This

- You have Kodi running on multiple devices (living room, bedroom, office)
- You already use a shared MySQL/MariaDB video database for your Kodi library
- You want your "next episode" to be consistent everywhere

### When You Don't Need This

- You only use Kodi on one device
- Each device has its own separate library
- You use Kodi profiles to separate users (profiles already have separate settings)

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Kodi** | 21 (Omega) or later on all devices |
| **Shared Database** | MySQL or MariaDB configured as Kodi's video database |
| **pymysql Addon** | `script.module.pymysql` (bundled with EasyTV) |
| **EasyTV** | The same version on all devices |

> **Important:** Multi-instance sync only works when Kodi is configured with a shared MySQL/MariaDB video database via `advancedsettings.xml`. If you're using Kodi's default SQLite database, this feature is not available.

---

## How It Works

### The Big Picture

EasyTV creates its own database alongside your Kodi video database:

```
Your MySQL/MariaDB Server
  ├── myvideos131          ← Kodi's video library (shared)
  └── easytv_myvideos      ← EasyTV sync data (shared)
```

Every time you watch an episode, EasyTV writes the updated "next episode" to this shared database. Other instances detect the change via a revision counter and refresh their local data.

### Auto-Detection

EasyTV reads your database connection details directly from Kodi's `advancedsettings.xml`. You don't need to enter any credentials. If Kodi can connect to your shared database, so can EasyTV.

The following paths are checked (in order):
1. `special://userdata/advancedsettings.xml`
2. `special://profile/advancedsettings.xml`
3. `special://masterprofile/advancedsettings.xml`

### Database Strategy

EasyTV tries two approaches for storing sync data:

1. **Preferred:** Create a dedicated `easytv_{kodi_db_name}` database (e.g., `easytv_myvideos`)
2. **Fallback:** If the database user lacks `CREATE DATABASE` permission, EasyTV creates prefixed tables inside Kodi's existing video database

Both approaches work identically. The fallback happens automatically and requires no user intervention.

### Staleness Detection

Each write increments a global revision counter. Before showing data, each instance compares its local revision with the database revision. If they differ, the instance refreshes. This is an O(1) check that adds virtually no overhead.

---

## Setup Guide

### Prerequisites

1. **Verify your shared database is working.** In Kodi, go to Settings and confirm your TV shows are loaded from the shared MySQL/MariaDB database. If you can see your library, the database is working.

2. **Ensure EasyTV is installed on all devices.** Run the same EasyTV version on every device so they agree on tracking format.

### Enable Sync

On **each** Kodi device:

1. Go to **Settings → Advanced → Multi-Instance Sync**
2. Toggle on **Enable multi-instance sync**
3. Restart Kodi (recommended for first-time setup)

<!-- Capture the Settings -> Advanced -> Multi-Instance Sync panel and drop in as multi-instance-sync-settings.png, then uncomment:
![Multi-instance sync settings](assets/screenshots/multi-instance-sync-settings.png)
-->



### Verify It's Working

After enabling sync and restarting:

1. Enable debug logging: **Settings → Advanced → Debugging → Enable debug logging**
2. Check the log file for these entries:
   ```
   [EasyTV.storage] INFO: Using shared database storage, database=easytv_myvideos
   [EasyTV.shareddb] INFO: Connected to database, host=your-db-host, port=3306
   ```
3. Watch an episode on one device
4. Check that the other device shows the correct next episode

### First-Time Migration

When you first enable sync:
- If this is the first device, EasyTV writes all its current tracking data to the shared database
- If another device has already populated the database, this device syncs from the existing data
- A migration lock prevents two devices from trying to populate simultaneously

---

## Consistent Settings

For your "next episode" to be the same on all devices, certain settings must match across all Kodi instances:

### Settings That Must Match

| Setting | Why It Matters |
|---------|---------------|
| **[Random-order shows](random-order-shows.md)** | These shows pick a random episode instead of the next sequential one. Different selections = different "next" episodes. |
| **Include positioned specials** | Affects episode ordering. One device including specials and another excluding them will disagree on what's "next". |

### Settings That Don't Need to Match

These settings are purely local and can differ between devices:

- View style, sort order, show limits
- Launch behavior (Browse vs Random vs Ask)
- Playlist content, length, and filters
- Notification and prompt settings
- Debug logging

---

## Automatic Recovery

### Library Rebuilds

If you delete and rescan your Kodi library, show IDs change. EasyTV handles this automatically:

1. Detects that stored show IDs no longer exist in the library
2. Looks up shows by **title + year** to find their new IDs
3. Migrates tracking data to the new IDs
4. Clears episode lists (episode IDs also change during a rebuild)
5. Recomputes the next episode for affected shows

This process is logged at INFO level. Check the log if you want to verify it worked.

### Orphan Cleanup

On each startup, EasyTV compares stored shows against the current library. Shows that no longer exist in Kodi's library are automatically removed from the sync database.

### Connection Recovery

If the database becomes temporarily unavailable:

1. EasyTV enters a 30-second backoff period
2. A warning is logged and local cache is used
3. After the backoff, EasyTV retries the connection
4. When the connection is restored, a full refresh occurs

If the database connection drops during overnight idle (common with MariaDB), EasyTV automatically re-establishes the connection and re-selects the database.

---

## Clearing Sync Data

You can clear all shared sync data if you need a fresh start:

1. Go to **Settings → Advanced → Multi-Instance Sync**
2. Click **Clear sync data...**
3. Confirm the action

This deletes all show tracking data from the shared database and resets the revision counter. The next service restart will repopulate the data.

### When to Clear Sync Data

- After a major library reorganization
- If sync data appears corrupted or inconsistent
- When troubleshooting persistent sync issues
- When switching from one shared database to another

> **Note:** Clearing sync data affects **all** connected devices. Each device will rebuild its tracking data on next restart.

---

## Limitations

| Limitation | Details |
|------------|---------|
| **Clones don't sync** | [Clones](clones.md) use the main addon's background service data locally. They don't participate in multi-instance sync. |
| **Settings must match** | Random-order shows and positioned specials must be configured identically on all devices for consistent results. |
| **Requires shared MySQL/MariaDB** | SQLite (Kodi's default) doesn't support multi-device access. |
| **pymysql required** | The `script.module.pymysql` addon must be available. It's bundled with EasyTV but must be importable. |
| **One-way episode tracking** | Sync shares which episode is "next". It doesn't sync Kodi's watch status, which is handled by Kodi's own shared database. |

---

## Troubleshooting

### "pymysql not available"

EasyTV shows a dialog saying pymysql is missing.

**Solution:**
1. Check that `script.module.pymysql` is installed in Kodi
2. It should be installed automatically as a dependency of EasyTV
3. If missing, install it manually from the Kodi addon repository
4. Restart Kodi

### Database Unavailable After Enabling Sync

EasyTV falls back to local mode with a warning in the log.

**Check:**
1. Verify Kodi can access the shared database (your library loads normally)
2. Check `advancedsettings.xml` exists and contains `<videodatabase>` with `<type>mysql</type>`
3. Check the log for specific error messages:
   ```
   [EasyTV.shareddb] WARNING: Database unavailable, backing off
   ```
4. Verify the database server is running and accessible from this device

### Devices Not Syncing

One device updates but others don't reflect the change.

**Check:**
1. Multi-instance sync is enabled on **all** devices
2. All devices point to the **same** MySQL/MariaDB server and database
3. All devices are running the same EasyTV version
4. Check logs on each device for `Using shared database storage` (should appear) vs `Using window property storage` (means sync isn't active)

### "Next Episode" Differs Between Devices

Devices show different next episodes for the same show.

**Check:**
1. Compare random-order show selections. They must be identical on all devices.
2. Compare the "Include positioned specials" setting. It must match on all devices.
3. If settings match, try clearing sync data and letting devices repopulate

---

## Related Pages

- **[Installation](installation.md):** Setting up EasyTV
- **[Settings Reference](settings-reference.md):** Multi-instance sync settings
- **[Clones](clones.md):** Why clones don't participate in sync
- **[Random-Order Shows](random-order-shows.md):** Must match across devices
- **[Troubleshooting](troubleshooting-and-faq.md):** More troubleshooting tips
