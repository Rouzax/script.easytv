# EasyTV - Claude Code Project Instructions

## Project Overview

**EasyTV** is a Kodi addon providing "channel surfing" functionality for TV show libraries. It tracks the next episode to watch for every TV show and enables lean-back viewing through randomized playlists. The addon consists of a script component with a background service.

- **Addon ID:** `script.easytv`
- **Repository:** https://github.com/Rouzax/script.easytv
- **License:** GPL-3.0-only
- **Original Author:** KODeKarnage (LazyTV)

## ⚠️ IMPORTANT: Ask First, Code Later

Before writing any code, always:

1. **Clarify requirements** — Ask questions if anything is unclear or ambiguous
2. **Confirm understanding** — Summarize what you plan to do and get approval
3. **Identify scope** — Check if the task is larger than it appears
4. **Discuss approach** — For non-trivial changes, propose the solution before implementing

Only start coding after requirements are clear and approach is agreed upon.

## Development Workflow Skills

The following skills are available and must be used in the appropriate context:

| Situation | Skill | Why |
|-----------|-------|-----|
| New feature or behavior change | `brainstorming` | Explore intent, requirements, and design before coding |
| Any implementation (feature or bugfix) | `test-driven-development` | Write tests first, then implement |
| Bug, test failure, unexpected behavior | `systematic-debugging` | Diagnose root cause before proposing fixes |
| Implementation plan ready to execute | `executing-plans` | Follow the plan with review checkpoints |
| Work complete, ready to integrate | `finishing-a-development-branch` | Decide on merge, PR, or cleanup |
| Before claiming work is done | `verification-before-completion` | Run verification commands, confirm output |

## Environment & Compatibility

| Requirement | Value |
|-------------|-------|
| Target Platform | Kodi 21+ (Omega) |
| Python Version | 3.8+ (Windows builds use 3.8, other platforms use 3.11+) |
| Addon Version | 1.0.0+ |

### Critical Python 3.8 Constraints

**DO NOT USE** these Python 3.10+ features (they break on Kodi Windows builds):
- Union type syntax: `X | Y` → Use `Union[X, Y]` from typing
- Optional syntax: `X | None` → Use `Optional[X]` from typing
- `match`/`case` statements
- `list[int]` in type aliases → Use `List[int]` from typing
- Parenthesized context managers with commas

**Note:** `from __future__ import annotations` only defers evaluation for function annotations, NOT for type alias assignments like `Callback = Callable[[list[int]], None]`.

### Backward Compatibility Policy

We have an install base. Be mindful of breaking changes:
- Maintain settings/data compatibility within major versions (1.x.x)
- Breaking changes require major version bump (2.0.0)
- New settings must have sensible defaults for existing users
- Existing smart playlists and user configurations must continue to work

## Development Tools

The following tools are installed on the development machine and available for use:

| Tool | Version | Purpose |
|------|---------|---------|
| **Kodistubs** | 21.0.0 | Stub modules recreating Kodi Python API (`xbmc`, `xbmcgui`, `xbmcaddon`, `xbmcvfs`, `xbmcplugin`, `xbmcdrm`) — enables type checking and autocompletion |
| **pyright** | 1.1.408 | Static type checker (configured for Python 3.8 via `pyrightconfig.json`) |
| **pyflakes** | 3.4.0 | Fast static analysis for unused imports, undefined names |
| **ruff** | 0.15.5 | Fast linter and formatter (replaces flake8/isort/black) |
| **pytest** | 9.0.2 | Test framework |
| **pytest-mock** | 3.15.1 | Mocker fixture for pytest (wraps `unittest.mock`) |
| **coverage** | 7.13.4 | Code coverage measurement for pytest |
| **kodi-addon-checker** | 0.0.36 | Official Kodi repo pre-validation (addon.xml, images, PO files, dependencies, banned files) |

### Kodistubs

Kodistubs provides type stubs for the Kodi Python API. They are installed at `~/.local/lib/python3.12/site-packages/` and are automatically resolved by pyright. This means:
- `import xbmc`, `import xbmcgui`, etc. resolve without errors in type checking
- Function signatures, parameter types, and return types are available
- No runtime Kodi instance is needed for static analysis

### Ruff

Use ruff for quick linting beyond what pyflakes catches:
```bash
ruff check resources/lib/
```

## Verification

Run after every change:

```bash
# Combined validation — syntax check + static analysis
find . -name "*.py" -not -path "*/__pycache__/*" \
  -exec python3 -m py_compile {} \; && \
echo "Syntax OK" && \
pyflakes $(find . -name "*.py" -not -path "*/__pycache__/*")
```

Additional checks:

```bash
# Pyright type checking (respects pyrightconfig.json for Python 3.8)
pyright

# Syntax check only
find . -name "*.py" -exec python3 -m py_compile {} \;

# Static analysis only
pyflakes $(find . -name "*.py" -not -path "*/__pycache__/*")

# Kodi addon checker (official repo pre-validation)
kodi-addon-checker --branch omega .
```

## Testing

Tests live in `tests/` and use pytest. Kodistubs provide runtime Kodi API stubs — no mocking needed for imports.

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a specific test file
python3 -m pytest tests/test_utils.py -v
```

Guidelines:
- When writing new pure logic functions, add corresponding tests
- When fixing bugs, add a regression test
- `tests/conftest.py` handles sys.path setup and logger reset

## Architecture

Modular structure under `resources/lib/`:

| Package | Responsibility |
|---------|---------------|
| `service/` | Background service: daemon loop, settings, episode tracking, library monitoring, playback monitoring |
| `data/` | Data layer: JSON-RPC queries, show processing, smart playlists, duration caching, shared database sync, storage abstraction |
| `ui/` | User interface: browse window, dialogs, context menu |
| `playback/` | Playback: random playlist builder, browse mode orchestrator, browse mode player, playlist session tracking |
| `utils.py` | Shared utilities, StructuredLogger |
| `constants.py` | Centralized constants |

Entry points: `default.py` (UI), `service.py` (background service)

Supporting scripts in `resources/`: `selector.py`, `clone.py`, `update_clone.py`, `episode_exporter.py`, `playlists.py`, `clear_sync_data.py`

### Architectural Rules

- Service logic stays in `service/`, UI logic in `ui/`
- Data access goes through `data/`, not direct JSON-RPC calls elsewhere
- Shared utilities in `utils.py`, constants in `constants.py`
- Avoid cross-package dependencies where possible (e.g., `ui/` shouldn't import from `service/`)
- Known cross-package exceptions:
  - `playback/browse_mode.py` imports from `ui/` as a feature orchestrator
  - `service/playback_monitor.py` imports from `playback/` for playlist session tracking
  - `service/daemon.py` conditionally imports from `playback/` for show filtering
  - `data/shows.py` imports `PROP_DURATION` constant from `service/episode_tracker.py`

### Entry Point Invocations

| Entry Point | Invocation |
|-------------|------------|
| Main UI | `RunScript(script.easytv)` |
| Background service | Kodi service extension (auto-start) |
| Playlist selector | `RunScript(script.easytv,playlist)` |
| Show selector | `RunScript(script.easytv,selector)` |
| Clone creator | `RunScript(script.easytv,clone)` |
| Episode exporter | `RunScript(script.easytv,exporter)` |
| Clear sync data | `RunScript(script.easytv,clear_sync_data)` |

## Code Standards

- Follow SOLID, DRY, KISS principles
- Add type hints where practical (Python 3.8 compatible)
- No duplicate code or functions — check `utils.py` and `constants.py` first
- Clear, descriptive naming
- All modules should have docstrings with Logging section
- Dead code policy: if code isn't used within the addon, remove it. No keeping unused functions "for potential future use."

### Language Strings

Language strings are used in **two locations** — both must be checked:

| Location | Pattern | Example |
|----------|---------|---------|
| Python files | `lang(XXXXX)` | `lang(32220)` |
| Skin XML files | `$ADDON[script.easytv XXXXX]` | `$ADDON[script.easytv 32220]` |

Before removing "unused" strings from `strings.po`:
```bash
grep -r "lang(32XXX)" resources/lib/
grep -r "32XXX" resources/skins/
```

### Settings Language Consistency

EasyTV and EasyMovie are sibling addons that share a settings vocabulary.
When adding or changing any setting label or help text:

1. **Check the sibling addon** — look at the equivalent setting in `/home/martijn/script.easymovie/resources/language/resource.language.en_gb/strings.po`
2. **Use the same wording** for equivalent concepts (see conventions below)
3. **Every user-facing setting must have help text** — no empty `help=""` attributes

| Concept | Convention |
|---------|-----------|
| Launch action | "When I open [addon]" |
| Return after play | "Return to [addon] after playback" |
| Countdown | "Countdown duration (seconds)" / "If countdown expires" |
| Resume | "Seek to resume point for [content]" |
| In-progress | "Start playlist with unfinished [content]" |
| Debug logging | "Write detailed diagnostic information to a separate log file" |
| Clone | "Create [addon] copy..." |
| Theme help | "Choose the accent color theme for [addon] windows and dialogs" |
| Playback notification | "Show a notification with title and details when a [content item] starts playing" |

## Logging

See `LOGGING.md` for full documentation.

| Level | When to Use | Kodi Log | easytv.log |
|-------|-------------|----------|------------|
| ERROR | Operation failures | ✓ Always | ✓ Always |
| WARNING | Recoverable issues | ✓ Always | ✓ Always |
| INFO | Lifecycle events | ✓ Always | ✓ Always |
| DEBUG | Diagnostics | ✗ Never | ✓ When enabled |

Log file: `special://profile/addon_data/script.easytv/logs/easytv.log`

Usage pattern:
```python
from resources.lib.utils import get_logger

log = get_logger('module_name')

log.info("Service started", event="service.start", version=VERSION)
log.debug("Processing shows", count=len(shows))
log.warning("Show not found", show_id=123)
log.exception("Operation failed", event="operation.fail")  # In except blocks
```

Event naming: `domain.action` (e.g., `service.start`, `playlist.create`, `playback.complete`)

### Logger Names by Package

| Package | Logger Names |
|---------|-------------|
| `service/` | `'daemon'`, `'episode_tracker'`, `'library_monitor'`, `'playback_monitor'`, `'settings'` |
| `data/` | `'data'`, `'shareddb'`, `'storage'` |
| `ui/` | `'ui'` |
| `playback/` | `'playback'` |
| Entry points | `'default'`, `'clone'`, `'selector'`, `'export'`, `'playlists'`, `'clear_sync'` |

## Kodi-Specific Patterns

### Service-UI Communication

Use window properties for cross-component data sharing:
```python
# Service writes
xbmcgui.Window(10000).setProperty('EasyTV.123.title', 'Episode Title')

# UI reads
title = xbmcgui.Window(10000).getProperty('EasyTV.123.title')
```

### Settings Dialog Cache Issue

Kodi's settings dialog maintains an in-memory cache. When using `<close>true</close>` in action buttons followed by `setSetting()` and `openSettings()`, subsequent manual reopens may show stale values. Workaround: use window properties as intermediaries for the service to process after dialog truly closes.

### JSON-RPC Queries

Use centralized query builders in `data/queries.py`:
```python
from resources.lib.utils import json_query
from resources.lib.data.queries import build_show_episodes_query

result = json_query(build_show_episodes_query(show_id))
```

See `.claude/performance.md` for JSON-RPC performance benchmarks and optimization guidelines.

## Kodi Test Instances

| Host | URL | Purpose |
|------|-----|---------|
| vm2 | http://vm2.home.lan:8080/jsonrpc | Primary test instance (MariaDB backend) |

Claude Code can query Kodi directly via curl:
```bash
curl -s -X POST http://vm2.home.lan:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"limits":{"start":0,"end":1}},"id":1}'
```

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Coding before understanding | Ask clarifying questions first |
| Using `X \| Y` union syntax | Use `Union[X, Y]` for Python 3.8 |
| Using `list[int]` in type aliases | Use `List[int]` from typing |
| Creating duplicate utility functions | Check utils.py and constants.py first |
| Not handling settings cache issue | Use window properties for action results |
| Logging without structured data | Use `log.method("msg", key=value)` pattern |
| Not calling `log.exception()` in except | Always use for automatic stack traces |
| Breaking settings compatibility | New settings need default values |
| N+1 JSON-RPC queries | Use bulk queries (see `.claude/performance.md`) |

## Wiki Maintenance

The project wiki lives at https://github.com/Rouzax/script.easytv.wiki.git

When changes affect user-facing behavior, settings, or features:

1. Clone the wiki repo alongside the main repo:
   git clone https://github.com/Rouzax/script.easytv.wiki.git /tmp/easytv-wiki
2. Update the relevant wiki pages
3. Commit and push

Wiki pages to keep in sync:
- Feature changes → update relevant feature page
- New settings → update Settings page
- Changed behavior → update relevant usage page
- New clone/playlist functionality → update relevant guide

## Packaging (Kodi-Installable Zip)

Build a zip from the repo parent directory. The zip **must** contain only files Kodi needs — nothing else.

```bash
cd /home/martijn && \
version=$(python3 -c "
from xml.etree import ElementTree as et
tree = et.parse('script.easytv/addon.xml')
print(tree.getroot().get('version'))
") && \
zip -r "script.easytv-${version}.zip" script.easytv/ \
  -x "script.easytv/.git/*" \
  -x "script.easytv/.git*" \
  -x "script.easytv/.github/*" \
  -x "script.easytv/.claude/*" \
  -x "script.easytv/.claudeignore" \
  -x "script.easytv/.mcp.json" \
  -x "script.easytv/CLAUDE.md" \
  -x "script.easytv/CONTRIBUTING.md" \
  -x "script.easytv/LOGGING.md" \
  -x "script.easytv/README.md" \
  -x "script.easytv/pyrightconfig.json" \
  -x "script.easytv/.pyflakes" \
  -x "script.easytv/docs/*" \
  -x "script.easytv/docs/" \
  -x "script.easytv/__pycache__/*" \
  -x "script.easytv/**/__pycache__/*" \
  -x "script.easytv/*.log" \
  -x "script.easytv/_temp/*" \
  -x "script.easytv/_temp/" \
  -x "script.easytv/.worktrees/*" \
  -x "script.easytv/.worktrees/" \
  -x "script.easytv/.ruff_cache/*" \
  -x "script.easytv/.ruff_cache/" \
  -x "script.easytv/.pytest_cache/*" \
  -x "script.easytv/.pytest_cache/" \
  -x "script.easytv/tests/*" \
  -x "script.easytv/tests/" \
  -x "script.easytv/conftest.py" \
  -x "script.easytv/pytest.ini"
```

**Include** (Kodi needs these):
- `addon.xml`, `default.py`, `service.py` — manifest and entry points
- `resources/` — settings, skins, language, lib, scripts, clone templates
- `icon.png`, `fanart.jpg` — addon artwork
- `LICENSE.txt`, `changelog.txt` — metadata Kodi displays

**Exclude** (dev/CI tooling, never ship):
- `.git/`, `.github/`, `.gitignore` — version control
- `.claude/`, `.claudeignore`, `.mcp.json`, `CLAUDE.md` — Claude Code / MCP config
- `CONTRIBUTING.md`, `LOGGING.md`, `README.md` — dev docs
- `pyrightconfig.json`, `.pyflakes` — linter/type-checker config
- `docs/` — example smart playlists, not part of the addon
- `__pycache__/`, `*.log` — build artifacts and logs
- `_temp/` — temporary working directory
- `.worktrees/` — git worktree checkouts
- `.ruff_cache/` — ruff linter cache
- `.pytest_cache/` — pytest cache
- `tests/` — pytest test suite
- `conftest.py`, `pytest.ini` — pytest configuration

If you add a new dev-only file to the repo root, **add it to the exclude list above**.

## Release Process

Use `/release` to run the full release workflow: validation, changelog/addon.xml finalization, git commit+tag+push, zip packaging, and GitHub release creation. Writing rules and templates are in `.claude/release-template.md`.

## Reference Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | User documentation, feature overview |
| `LOGGING.md` | Logging architecture and guidelines |
| `CONTRIBUTING.md` | Contribution guidelines |
| `changelog.txt` | Version history |
| `.claude/performance.md` | JSON-RPC performance benchmarks |
| `.claude/kodi-patterns.md` | Kodi development patterns and gotchas |
| `.claude/skin-guidelines.md` | Dialog/skin design standards, colors, animations |
