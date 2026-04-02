# Clone Shared DB Access and Premiere Filter Resume Fix

**Date:** 2026-04-02
**Status:** Approved
**Target:** v1.5.2~alpha2

## Problem

### Issue 1: Clone sync-before-browse is dead code

The v1.5.2~alpha1 sync fix (`sync_show_list_from_shared_db()` called before browse/playlist)
never executes in clones. The code path:

1. `get_storage()` checks `multi_instance_sync` setting
2. Clones don't have this setting (it's a service setting, clones have no service)
3. `get_storage()` returns `WindowPropertyStorage`
4. `WindowPropertyStorage.needs_refresh()` always returns `False`
5. `sync_show_list_from_shared_db()` never runs

The clone relies entirely on window properties set by the main service during
`bulk_refresh` (triggered by library scans). If no scan happened since a new
episode appeared or was watched on another instance, the clone sees stale data.

### Issue 2: Premiere filter ignores resume state

The `should_include()` function in `browse_mode.py` filters out any show whose
next episode has `episode_num == 1`, regardless of whether the user is actively
watching that episode. This caused The Pitt S02E01 (44% resume point from
another instance) to be invisible in browse mode.

The smart playlist logic already handles this correctly (commit `6132aaf`
categorizes partially-watched premieres as continue_watching), but the browse
mode premiere filter is a separate code path that doesn't check resume state.

## Design

### Part 1: Service advertises shared DB location

When the main service's `SharedDatabase` successfully connects and initializes
its schema, it writes two window properties on `Window(10000)`:

```
EasyTV.SharedDB.db_name      = "easytv_mastervideo"   (resolved DB name)
EasyTV.SharedDB.table_prefix = ""                       (empty if separate DB, prefix if fallback)
```

**No credentials in window properties.** The clone reads MySQL host/port/user/password
from `advancedsettings.xml` using the existing `SharedDatabase._parse_advancedsettings()`
code path. Both main addon and clone run on the same Kodi instance, so they read
the same file.

Presence of `EasyTV.SharedDB.db_name` means "shared DB is active and reachable."

### Part 2: Clone storage initialization

`get_storage()` gains a fallback path for clones:

```
get_storage()
  -> check multi_instance_sync setting -> found and true?
     -> YES: existing SharedDatabaseStorage path (main addon)
     -> NO:  check EasyTV.SharedDB.db_name window property -> found?
        -> YES: parse advancedsettings.xml for credentials,
                create SharedDatabaseStorage with advertised db_name + table_prefix
        -> NO:  WindowPropertyStorage (service not running or sync disabled)
```

The main addon's flow is unchanged. The window property check is a clone-only
fallback. The clone gets the same `SharedDatabaseStorage` instance with the same
capabilities. Existing `sync_show_list_from_shared_db()` and
`get_ondeck_bulk(refresh_display=True)` calls in `browse_mode.py` and
`random_player.py` will now actually execute.

### Part 3: Premiere filter resume check

`should_include()` in `browse_mode.py` checks resume state before applying the
premiere filter:

```
Current:  episode_num == 1 -> check SKIP setting -> exclude
Proposed: episode_num == 1 -> has resume? -> YES: include (user is watching)
                                          -> NO:  check SKIP setting as before
```

Resume state is already available as window property `EasyTV.{show_id}.Resume`
(set to `"true"` or `"false"` by `cache_next_episode()`).

### Part 4: Cleanup on shutdown/failure

The service clears `EasyTV.SharedDB.db_name` and `EasyTV.SharedDB.table_prefix`
in three scenarios:

1. **DB becomes unavailable** - on connection failure (alongside existing backoff logic)
2. **Service shuts down** - during shutdown sequence
3. **User disables multi_instance_sync** - when `reset_storage()` is called (daemon line 1722-1723)

This ensures clones fall back to WindowPropertyStorage gracefully when the
shared DB is not reachable.

### Part 5: Diagnostic logging

Logging gaps identified during RCA that made diagnosis harder than necessary:

**Premiere filter (browse_mode.py):**
- Summary after filtering: `"Premiere filter applied | before=160, after=5, excluded=155"`
- Log level: DEBUG

**Storage backend selection (storage.py get_storage()):**
- Clone connecting: `"Using shared database storage via advertised config | db_name=easytv_mastervideo"`
- Clone fallback: `"Shared DB not advertised, using window property storage"`
- Log level: INFO (same as existing `"Using window property storage"` message)

**Sync decision (browse_mode.py / random_player.py):**
- Sync skipped: `"Skipping shared DB sync | reason=local_storage"` or `"reason=not_stale"`
- Log level: DEBUG

**Service advertise/clear (shared_db.py / daemon.py):**
- On advertise: `"Shared DB config advertised | db_name=easytv_mastervideo"`
- On clear: `"Shared DB config cleared | reason=db_unavailable"` (or `shutdown`, `setting_disabled`)
- Log level: INFO

## What's NOT changing

- No new settings for clones - no `multi_instance_sync` in `settings_clone.xml`
- No writes from clones - clone code paths are all reads
- No changes to the main addon's primary storage flow
- No changes to how the service does bulk_refresh
- `advancedsettings.xml` parsing reuses existing `SharedDatabase._parse_advancedsettings()`
- Smart playlist premiere categorization unchanged

## Testing

- Unit test: `should_include()` with resume state + premiere combinations
- Unit test: `get_storage()` fallback path with/without advertised window properties
- Manual test: clone browse on multi-instance setup after cross-instance playback

## Files affected

| File | Change |
|------|--------|
| `resources/lib/data/storage.py` | `get_storage()` fallback path, logging |
| `resources/lib/data/shared_db.py` | Advertise/clear window properties after connect/disconnect |
| `resources/lib/service/daemon.py` | Clear advertised properties on shutdown/setting change |
| `resources/lib/playback/browse_mode.py` | `should_include()` resume check, premiere filter logging, sync skip logging |
| `resources/lib/playback/random_player.py` | Sync skip logging |
| `resources/lib/constants.py` | New property name constants for SharedDB advertisement |
| `tests/test_browse_mode.py` (new or existing) | Premiere filter + resume tests |
| `tests/test_storage.py` (new or existing) | get_storage() fallback tests |
