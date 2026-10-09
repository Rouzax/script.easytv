# Contributing to EasyTV

Thank you for your interest in contributing to EasyTV! This document outlines how you can help.

## Important Note

This project is maintained in my spare time. Response times may vary, and I may not be able to address every issue or request immediately. Your patience is appreciated!

---

## How to Contribute

### Reporting Bugs

Found something broken? Please open an issue with:

1. **Kodi version** (e.g., Kodi 21.1 Omega)
2. **Operating system** (e.g., Windows 11, LibreELEC 12, etc.)
3. **Steps to reproduce** the problem
4. **Expected behavior** vs **actual behavior**
5. **Log file** if possible (see [LOGGING.md](LOGGING.md) for how to enable debug logging)

[Open a bug report →](https://github.com/Rouzax/script.easytv/issues/new)

### Suggesting Features

Have an idea? Open an issue describing:

1. **What** you'd like to see
2. **Why** it would be useful
3. **How** you envision it working

I can't promise every feature will be implemented, but I do read all suggestions.

[Suggest a feature →](https://github.com/Rouzax/script.easytv/issues/new)

### Pull Requests

#### Skins
I'm not a skinner, so **skin contributions and improvements are especially welcome!** The default skin files are in:
```
resources/skins/Default/1080i/
```

If you create or improve a skin, please submit a PR.

#### Code Changes
For code changes:

1. **Open an issue first** to discuss the change
2. Fork the repository
3. Create a branch for your changes
4. Follow the existing code style
5. Test your changes in Kodi
6. Submit a pull request

Please keep PRs focused — one feature or fix per PR makes review easier.

---

## Issue Labels and Milestones

Labels say what an issue is or what it is waiting on. Milestones say when it is expected to ship.

**Labels**

| Label | Meaning |
|-------|---------|
| `bug` | Something isn't working. Set automatically by the bug report form. |
| `enhancement` | A new feature or improvement. Set automatically by the feature request form. |
| `documentation` | The docs need changing, not the add-on. |
| `needs-info` | Waiting on the reporter. The issue may be closed if the details never arrive. |
| `needs-upstream` | Waiting on Kodi or a skin. EasyTV cannot fix it on its own. |
| `duplicate`, `invalid`, `wontfix` | Why an issue was closed without a change. |

**Milestones**

| Milestone | Meaning |
|-----------|---------|
| Next | Planned for the coming release. At release it is renamed to that version and closed, and a new Next is opened. |
| Later | Accepted, but not planned for a particular release yet. |

An issue without a milestone has not been triaged yet. Open milestones do not promise a version number; closed milestones record what each release shipped, and [changelog.txt](changelog.txt) describes the changes.

The label list lives in [.github/sync-labels.sh](.github/sync-labels.sh). Change labels there and run the script, rather than editing them on GitHub.

---

## Code Style

- Python 3.11+ compatible (Kodi 21 minimum)
- Type hints where practical
- Clear, descriptive naming
- Follow existing patterns in the codebase

---

## Development Setup

1. Clone the repository
2. Install [Kodistubs](https://pypi.org/project/Kodistubs/) for IDE support:
   ```bash
   pip install Kodistubs
   ```
3. Symlink or copy to your Kodi addons folder for testing

---

## Project Structure

```
script.easytv/
├── addon.xml               # Kodi addon metadata
├── default.py              # UI entry point (browse/random playlist)
├── service.py              # Background service entry point
└── resources/
    ├── settings.xml        # Settings definition (Kodi 21+ format)
    ├── addon_clone.xml     # Clone addon metadata template
    ├── settings_clone.xml  # Clone addon settings template
    ├── *.py                # Script entry points: show/playlist/genre selectors,
    │                       #   clone create/update, episode export, clear sync data,
    │                       #   dialog preview
    ├── icons/              # Theme icons
    ├── language/           # Localization strings (strings.po)
    ├── skins/Default/
    │   ├── 1080i/          # Window and dialog XML
    │   └── media/          # Skin textures
    └── lib/                # Core library
        ├── constants.py    # All magic values
        ├── utils.py        # Shared utilities (logging, JSON-RPC, settings)
        ├── data/           # JSON-RPC queries, show processing, smart playlists,
        │                   #   caches, storage, multi-instance sync database
        ├── service/        # Background service: daemon loop, settings, episode
        │                   #   tracking, library and playback monitoring
        ├── ui/             # Browse window, dialogs, context menu, guided-flow wizard
        └── playback/       # Random playlist builder, browse mode, playlist sessions
```

Each module starts with a docstring describing its responsibility; read those for the detail below package level.

---

## Architecture Principles

1. **Entry points are minimal** — `default.py` and `service.py` contain only argument parsing and delegation to library modules

2. **No global settings** — Settings are loaded inside functions when needed, never at module level

3. **Structured logging** — Use `get_logger()` from utils.py; logs include context via keyword arguments. See [LOGGING.md](LOGGING.md) for guidelines.

4. **Constants centralized** — All magic values live in `constants.py`

5. **Dependency injection** — Core classes accept dependencies (addon, logger, window) as constructor parameters

---

## Adding New Features

1. **Add constants** to `resources/lib/constants.py`
2. **Add settings** to `resources/settings.xml` and localization strings
3. **Add data access** to appropriate module in `resources/lib/data/`
4. **Add UI** to appropriate module in `resources/lib/ui/`
5. **Wire up** in entry points or service daemon

---

## Window Properties

EasyTV stores episode metadata in Kodi window properties for inter-process communication between the service and UI. These properties can be used by skins or other addons.

| Property                            | Format         | Description                                 |
| ----------------------------------- | -------------- | ------------------------------------------- |
| `EasyTV.{showid}.Title`             | string         | Episode title                               |
| `EasyTV.{showid}.TVShowTitle`       | string         | TV show title                               |
| `EasyTV.{showid}.Season`            | "01"-"99"      | Season number (zero-padded)                 |
| `EasyTV.{showid}.Episode`           | "01"-"99"      | Episode number (zero-padded)                |
| `EasyTV.{showid}.EpisodeNo`         | "s01e01"       | Combined season/episode string              |
| `EasyTV.{showid}.File`              | path           | Path to the episode file                    |
| `EasyTV.{showid}.Resume`            | "true"/"false" | Whether episode has partial progress        |
| `EasyTV.{showid}.PercentPlayed`     | "0%"-"100%"    | Percentage watched                          |
| `EasyTV.{showid}.Art(thumb)`        | path           | Episode thumbnail                           |
| `EasyTV.{showid}.Art(fanart)`       | path           | Show fanart                                 |
| `EasyTV.{showid}.Art(poster)`       | path           | Show poster                                 |
| `EasyTV.{showid}.IsSkipped`         | "true"/"false" | Whether this is a skipped (offdeck) episode |
| `EasyTV.{showid}.ondeck_list`       | "[id,...]"     | List of sequential episode IDs              |
| `EasyTV.{showid}.offdeck_list`      | "[id,...]"     | List of skipped episode IDs                 |
| `EasyTV.{showid}.unwatched_count`   | integer        | Number of unwatched episodes                |
| `EasyTV.{showid}.watched_count`     | integer        | Number of watched episodes                  |
| `EasyTV.ShowsWithUnwatchedEpisodes` | "[id,...]"     | List of show IDs with episodes              |

The `IsSkipped` property indicates when the displayed episode is from the "offdeck" list (skipped episodes that come before the user's current watch position). UI components can use this to display indicators like "Missed Episode" or visual badges.

---

## Testing Locally

Install the pinned dev tooling once, then run the same gate that pre-commit and CI run:

```bash
# Install the pinned dev tools
pip install -r requirements-dev.txt

# Lint + import sorting
ruff check

# Static analysis
pyflakes $(find . -name "*.py" -not -path "*/__pycache__/*")

# Type checking (Python 3.11 target)
pyright

# Dead-code detection
vulture resources/lib --min-confidence 80

# Tests + coverage
python3 -m pytest tests/ --ignore=tests/integration --cov=resources/lib
```

Or run the whole gate through pre-commit (recommended; install the hooks once):

```bash
pre-commit install && pre-commit install --hook-type pre-push
pre-commit run --all-files
```

---

## Questions?

If you're unsure about something, ask in the [Kodi forum thread](https://forum.kodi.tv/showthread.php?tid=383902), or open an issue if it concerns a change you want to make. I'd rather answer questions than have contributions go to waste.

Thanks for helping make EasyTV better!