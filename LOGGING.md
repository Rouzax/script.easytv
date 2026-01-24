# EasyTV Logging Guide

**Version:** 1.0  
**Last Updated:** 2025-01-15

This guide covers the logging system in EasyTV for both users and developers.

---

## For Users

### Enabling Debug Logging

1. Go to **Settings** → **Advanced** → **Debugging**
2. Enable **"Enable debug logging"**
3. Reproduce the issue you're troubleshooting
4. Find the log file at: `special://profile/addon_data/script.easytv/logs/easytv.log`

### Log File Location

The debug log is stored separately from Kodi's main log:

| Platform  | Typical Path                                                                           |
| --------- | -------------------------------------------------------------------------------------- |
| Windows   | `%APPDATA%\Kodi\userdata\addon_data\script.easytv\logs\easytv.log`                     |
| Linux     | `~/.kodi/userdata/addon_data/script.easytv/logs/easytv.log`                            |
| macOS     | `~/Library/Application Support/Kodi/userdata/addon_data/script.easytv/logs/easytv.log` |
| LibreELEC | `/storage/.kodi/userdata/addon_data/script.easytv/logs/easytv.log`                     |

### Log File Management

- Maximum file size: **500KB**
- Rotated files: `easytv.1.log`, `easytv.2.log`, `easytv.3.log`
- Older files are automatically deleted when rotated

### What Gets Logged Where

| Log Level   | When Debug OFF | When Debug ON         |
| ----------- | -------------- | --------------------- |
| **ERROR**   | Kodi log only  | Kodi log + easytv.log |
| **WARNING** | Kodi log only  | Kodi log + easytv.log |
| **INFO**    | Kodi log only  | Kodi log + easytv.log |
| **DEBUG**   | Not logged     | easytv.log only       |

This design keeps Kodi's log clean while giving you detailed debug information in a separate file.

---

## For Developers

### Architecture Overview

EasyTV uses a custom `StructuredLogger` class that provides:

1. **Dual output** — INFO/WARNING/ERROR go to Kodi log; DEBUG goes to file only
2. **Structured logging** — Key-value pairs for machine-readable context
3. **Event naming** — Consistent `domain.action` event taxonomy
4. **Thread safety** — All file operations are lock-protected
5. **Automatic rotation** — Files rotate at 500KB

### Getting a Logger

```python
from resources.lib.utils import get_logger

log = get_logger('module_name')
```

Logger names by package:

| Package      | Logger Name                                      |
| ------------ | ------------------------------------------------ |
| `service/`   | `'daemon'` or `'service'`                        |
| `ui/`        | `'ui'`                                           |
| `data/`      | `'data'`                                         |
| `playback/`  | `'playback'`                                     |
| Entry points | `'default'`, `'clone'`, `'selector'`, `'export'` |

### Log Levels

#### ERROR — Operation Failed

Use when an operation cannot complete. Always include `event=` with `.fail` suffix.

```python
log.error("Playlist write failed", 
          event="playlist.fail", 
          playlist=name, show=showname)
```

For exceptions, use `log.exception()` to auto-capture stack trace:

```python
try:
    risky_operation()
except Exception:
    log.exception("Operation failed", event="operation.fail", id=123)
```

#### WARNING — Unexpected but Handled

Use for fallback paths, missing data that's recovered, or unusual conditions.

```python
log.warning("Episode not in expected list", 
            event="playback.fallback",
            show_id=show_id, episode_id=ep_id)
```

#### INFO — Significant Events

Use for lifecycle events and user-visible actions. These appear in Kodi's log.

```python
log.info("Service started", event="service.start", version="4.0.9")
log.info("Playlist created", event="playlist.create", item_count=10)
```

#### DEBUG — Developer Details

Use freely for troubleshooting. Never appears in Kodi's log.

```python
log.debug("Processing shows", count=47)
log.debug("Episode found in ondeck list", position=3)
```

### Event Naming Convention

Events follow the pattern: `domain.action`

| Domain     | Used For            | Example Events                                       |
| ---------- | ------------------- | ---------------------------------------------------- |
| `service`  | Service lifecycle   | `service.start`, `service.stop`, `service.init`      |
| `settings` | Configuration       | `settings.load`, `settings.migrate`, `settings.id_shift`, `settings.validation_complete`, `settings.orphan_cleanup` |
| `library`  | Kodi library        | `library.refresh`, `library.fallback`                |
| `playback` | Video playback      | `playback.start`, `playback.fallback`                |
| `playlist` | Playlist operations | `playlist.create`, `playlist.start`, `playlist.fail` |
| `next`     | Next episode logic  | `next.pick`, `next.fallback`                         |
| `clone`    | Clone operations    | `clone.create`, `clone.update`, `clone.fail`         |
| `export`   | Episode export      | `export.start`, `export.complete`, `export.fail`     |
| `ui`       | User interface      | `ui.open`, `ui.select`, `ui.fallback`                |
| `selector` | Show selector       | `selector.open`, `selector.save`                     |

### When to Add Logging

Add **INFO** logging for:
- Service/addon lifecycle events (start, stop, shutdown)
- User-initiated actions that complete successfully
- Configuration changes

Add **WARNING** logging for:
- Fallback paths taken (missing data, using defaults)
- Recoverable errors
- Unexpected but handled conditions

Add **ERROR** logging for:
- Operations that fail and cannot be recovered
- File I/O failures
- Critical missing dependencies

Add **DEBUG** logging for:
- Function entry with key parameters
- Loop iterations and counts
- Algorithm decisions
- Data transformations
- Timing information

### Timing Operations

Use `log_timing()` for expensive operations:

```python
from resources.lib.utils import get_logger, log_timing

log = get_logger('daemon')

with log_timing(log, "retrieve_show_ids"):
    result = json_query(get_unwatched_shows_query(), True)
```

This logs operation start and duration at DEBUG level.

For operations with multiple phases, use the `timer.mark()` method:

```python
with log_timing(log, "bulk_refresh", show_count=277) as timer:
    # Phase 1: Query shows
    result = json_query(get_shows_by_lastplayed_query(), True)
    timer.mark("show_query")
    
    # Phase 2: Query episodes
    episodes = json_query(build_all_episodes_query(), True)
    timer.mark("episode_query")
    
    # Phase 3: Process data
    process_episodes(episodes)
    timer.mark("processing")

# Logs: bulk_refresh completed | duration_ms=1500, show_count=277,
#       show_query_ms=50, episode_query_ms=800, processing_ms=650
```

### Standard Timing Events

The following timing events are defined in the daemon module:

| Event | Description | Phases |
|-------|-------------|--------|
| `bulk_refresh` | Startup/rescan with all shows | `show_query_ms`, `episode_query_ms`, `processing_ms`, `playlists_ms` |
| `show_refresh` | Single show refresh (playback tracking) | `show_query_ms`, `episode_query_ms`, `processing_ms` |
| `retrieve_show_ids` | Fetching show IDs from library | (no phases) |

**Example bulk_refresh output:**
```
bulk_refresh completed | duration_ms=1500, show_count=277,
    show_query_ms=50, episode_query_ms=800, processing_ms=600, playlists_ms=50
```

**Example show_refresh output:**
```
show_refresh completed | duration_ms=45, show_count=1,
    show_query_ms=10, episode_query_ms=20, processing_ms=15
```

### Module Docstrings

Every module with logging should include a Logging section:

```python
"""
Module description here.

Logging:
    Logger: 'module_name'
    Key events:
        - domain.action (LEVEL): Description
        - domain.other (LEVEL): Description
    See LOGGING.md for full guidelines.
"""
```

### Anti-Patterns to Avoid

❌ **Don't log sensitive data:**
```python
# BAD
log.debug("User credentials", password=user_password)
```

❌ **Don't use print():**
```python
# BAD
print("Debug info")

# GOOD
log.debug("Debug info")
```

❌ **Don't forget event= for INFO/WARNING/ERROR:**
```python
# BAD - missing event
log.info("Service started")

# GOOD
log.info("Service started", event="service.start")
```

❌ **Don't use error() in except blocks:**
```python
# BAD - loses stack trace
except Exception as e:
    log.error("Failed", error=str(e))

# GOOD - captures full trace
except Exception:
    log.exception("Failed", event="operation.fail")
```

❌ **Don't log in tight loops without throttling:**
```python
# BAD - floods log
for item in thousands_of_items:
    log.debug("Processing", item=item)

# GOOD - log summary
log.debug("Processing items", count=len(items))
for item in items:
    process(item)
log.debug("Processing complete")
```

### Log Output Format

#### Kodi Log
```
[EasyTV.module] message | event=domain.action, key=value, ...
```

#### easytv.log File
```
2025-01-15 14:45:12.401 [INFO ] [EasyTV.module] message | event=domain.action, key=value
2025-01-15 14:45:12.402 [DEBUG] [EasyTV.module] developer details | count=47
```

---

## Troubleshooting

### Log File Not Created

1. Check that debug logging is enabled in settings
2. Verify the addon_data directory exists and is writable
3. Check Kodi's log for initialization errors

### Log File Too Large

The file auto-rotates at 500KB. If you're generating logs faster than expected, check for:
- Tight loops with logging
- Repeated operations that should be batched

### Missing Expected Logs

- **DEBUG** logs only appear when debug logging is enabled
- Check you're looking at the right file (easytv.log vs kodi.log)
- Verify the logger name matches what you expect

---

*For more information, see the [EasyTV README](README.md) and source code.*
