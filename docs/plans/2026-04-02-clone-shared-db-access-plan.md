# Clone Shared DB Access - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable clones to read the EasyTV shared DB for cross-instance sync, and fix the premiere filter to respect resume state.

**Architecture:** The main service advertises its resolved DB location (db_name, table_prefix) via window properties after schema init. `get_storage()` gains a fallback path: when `multi_instance_sync` setting is absent (clones), it checks for advertised config and creates a SharedDatabaseStorage using credentials from advancedsettings.xml. The premiere filter checks `EasyTV.{id}.Resume` before excluding premieres.

**Tech Stack:** Python 3.8+, Kodi window properties, pymysql, pytest

---

### Task 1: Add SharedDB advertisement constants

**Files:**
- Modify: `resources/lib/constants.py:492-505`

**Step 1: Add constants after the existing shared DB config block**

Add two new property name constants at line 505 (after `KODI_DEFAULT_VIDEO_DB_NAME`):

```python
# Advertised shared DB location (set by service, read by clones)
PROP_SHARED_DB_NAME = "EasyTV.SharedDB.db_name"
PROP_SHARED_DB_TABLE_PREFIX = "EasyTV.SharedDB.table_prefix"
```

**Step 2: Run validation**

Run: `pyflakes resources/lib/constants.py`
Expected: No errors

**Step 3: Commit**

```
git add resources/lib/constants.py
git commit -m "feat: add SharedDB advertisement window property constants"
```

---

### Task 2: Service advertises DB config after schema init

**Files:**
- Modify: `resources/lib/data/shared_db.py:531-638`

**Step 1: Add advertise and clear methods to SharedDatabase**

Add two methods after `_initialize_schema()` (around line 638):

```python
def advertise_config(self) -> None:
    """Advertise DB location via window properties for clone access."""
    WINDOW.setProperty(PROP_SHARED_DB_NAME, self._easytv_db_name)
    WINDOW.setProperty(PROP_SHARED_DB_TABLE_PREFIX, self._table_prefix)
    log.info("Shared DB config advertised",
             event="shareddb.advertise",
             db_name=self._easytv_db_name,
             table_prefix=self._table_prefix or "(none)")

@staticmethod
def clear_advertised_config(reason: str = "unknown") -> None:
    """Clear advertised DB config from window properties."""
    WINDOW.clearProperty(PROP_SHARED_DB_NAME)
    WINDOW.clearProperty(PROP_SHARED_DB_TABLE_PREFIX)
    log.info("Shared DB config cleared",
             event="shareddb.advertise_clear",
             reason=reason)
```

Add imports for the new constants at the top of the file (existing import block from constants.py).

**Step 2: Call advertise_config() after successful schema init**

In `_connect()` at line 426, after `self._schema_initialized = True`, add:

```python
self.advertise_config()
```

**Step 3: Call clear in is_available() failure path**

In `is_available()` at line 169 (the except block), after clearing sync_rev, add:

```python
SharedDatabase.clear_advertised_config(reason="db_unavailable")
```

**Step 4: Run validation**

Run: `pyflakes resources/lib/data/shared_db.py`
Expected: No errors

**Step 5: Commit**

```
git add resources/lib/data/shared_db.py
git commit -m "feat: service advertises shared DB location via window properties"
```

---

### Task 3: Clear advertised config on shutdown and setting change

**Files:**
- Modify: `resources/lib/service/daemon.py:455,1726-1733`
- Modify: `resources/lib/service/main.py:69-76`

**Step 1: Clear on setting change**

In `daemon.py`, inside the `if sync_changed:` block (line 1726), add before `reset_storage()`:

```python
if not new_sync_enabled:
    from resources.lib.data.shared_db import SharedDatabase
    SharedDatabase.clear_advertised_config(reason="setting_disabled")
```

**Step 2: Clear on service shutdown**

In `service/main.py`, after `daemon.run()` returns (line 69), add:

```python
# Clear shared DB advertisement so clones don't try stale config
from resources.lib.data.shared_db import SharedDatabase
SharedDatabase.clear_advertised_config(reason="shutdown")
```

This goes before the `log.info("Service stopped", ...)` line.

**Step 3: Run validation**

Run: `pyflakes resources/lib/service/daemon.py resources/lib/service/main.py`
Expected: No errors

**Step 4: Commit**

```
git add resources/lib/service/daemon.py resources/lib/service/main.py
git commit -m "fix: clear shared DB advertisement on shutdown and setting change"
```

---

### Task 4: get_storage() fallback path for clones

**Files:**
- Modify: `resources/lib/data/storage.py:779-835`
- Test: `tests/test_storage.py`

**Step 1: Write failing tests**

Add to `tests/test_storage.py`:

```python
class TestGetStorageCloneFallback:
    """Test get_storage() clone fallback via advertised shared DB config."""

    def setup_method(self):
        """Reset storage singleton before each test."""
        from resources.lib.data.storage import reset_storage
        reset_storage()

    def test_clone_uses_window_property_when_no_advertised_config(self, mocker):
        """Clone without advertised DB config falls back to WindowPropertyStorage."""
        from resources.lib.data import storage as storage_mod
        from resources.lib.data.storage import get_storage, WindowPropertyStorage

        mocker.patch.object(storage_mod, 'get_bool_setting', return_value=False)
        mock_window = mocker.patch.object(storage_mod, 'WINDOW')
        mock_window.getProperty.return_value = ''  # No advertised config

        result = get_storage()
        assert isinstance(result, WindowPropertyStorage)

    def test_clone_uses_shared_db_when_advertised(self, mocker):
        """Clone with advertised DB config creates SharedDatabaseStorage."""
        from resources.lib.data import storage as storage_mod
        from resources.lib.data.storage import (
            get_storage, SharedDatabaseStorage, PROP_SHARED_DB_NAME,
            PROP_SHARED_DB_TABLE_PREFIX,
        )

        mocker.patch.object(storage_mod, 'get_bool_setting', return_value=False)

        def fake_get_prop(key):
            props = {
                PROP_SHARED_DB_NAME: 'easytv_mastervideo',
                PROP_SHARED_DB_TABLE_PREFIX: '',
            }
            return props.get(key, '')
        mock_window = mocker.patch.object(storage_mod, 'WINDOW')
        mock_window.getProperty.side_effect = fake_get_prop

        # Mock SharedDatabase to avoid real DB connection
        mock_db_class = mocker.patch(
            'resources.lib.data.storage.SharedDatabase'
        )
        mock_db_instance = mock_db_class.return_value
        mock_db_instance.is_available.return_value = True

        result = get_storage()
        assert isinstance(result, SharedDatabaseStorage)

    def test_clone_falls_back_when_advertised_db_unavailable(self, mocker):
        """Clone falls back to WindowPropertyStorage if advertised DB is unreachable."""
        from resources.lib.data import storage as storage_mod
        from resources.lib.data.storage import (
            get_storage, WindowPropertyStorage, PROP_SHARED_DB_NAME,
            PROP_SHARED_DB_TABLE_PREFIX,
        )

        mocker.patch.object(storage_mod, 'get_bool_setting', return_value=False)

        def fake_get_prop(key):
            props = {
                PROP_SHARED_DB_NAME: 'easytv_mastervideo',
                PROP_SHARED_DB_TABLE_PREFIX: '',
            }
            return props.get(key, '')
        mock_window = mocker.patch.object(storage_mod, 'WINDOW')
        mock_window.getProperty.side_effect = fake_get_prop

        mock_db_class = mocker.patch(
            'resources.lib.data.storage.SharedDatabase'
        )
        mock_db_instance = mock_db_class.return_value
        mock_db_instance.is_available.return_value = False

        result = get_storage()
        assert isinstance(result, WindowPropertyStorage)
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_storage.py::TestGetStorageCloneFallback -v`
Expected: FAIL (PROP_SHARED_DB_NAME not importable, fallback path doesn't exist yet)

**Step 3: Implement the fallback in get_storage()**

In `storage.py`, add imports at top:

```python
from resources.lib.constants import PROP_SHARED_DB_NAME, PROP_SHARED_DB_TABLE_PREFIX
```

Replace the block at lines 800-804:

```python
    # Check if multi-instance sync is enabled
    if not get_bool_setting(SETTING_MULTI_INSTANCE_SYNC):
        _storage_instance = WindowPropertyStorage()
        log.info("Using window property storage", event="storage.init_local")
        return _storage_instance
```

With:

```python
    # Check if multi-instance sync is enabled (main addon path)
    if not get_bool_setting(SETTING_MULTI_INSTANCE_SYNC):
        # Clone fallback: check if main service advertised shared DB config
        advertised_db = WINDOW.getProperty(PROP_SHARED_DB_NAME)
        if not advertised_db:
            _storage_instance = WindowPropertyStorage()
            log.info("Shared DB not advertised, using window property storage",
                     event="storage.init_local")
            return _storage_instance

        # Main service advertised DB config - connect using advancedsettings.xml
        # credentials + advertised db_name/table_prefix
        advertised_prefix = WINDOW.getProperty(PROP_SHARED_DB_TABLE_PREFIX)
        try:
            from resources.lib.data.shared_db import SharedDatabase
            db = SharedDatabase()
            db._easytv_db_name = advertised_db
            db._table_prefix = advertised_prefix
            db._use_separate_db = (advertised_prefix == "")
            db._schema_initialized = True  # Skip schema init (main service owns this)
            if db.is_available():
                _storage_instance = SharedDatabaseStorage(db)
                log.info("Using shared database storage via advertised config",
                         event="storage.init_shared_clone",
                         db_name=advertised_db)
                return _storage_instance
        except Exception as e:
            log.warning("Failed to connect to advertised shared DB",
                        event="storage.clone_connect_error",
                        error=str(e))

        _storage_instance = WindowPropertyStorage()
        log.info("Advertised shared DB unavailable, using window property storage",
                 event="storage.init_local")
        return _storage_instance
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_storage.py::TestGetStorageCloneFallback -v`
Expected: All 3 PASS

**Step 5: Run full validation**

Run: `pyflakes resources/lib/data/storage.py && python3 -m pytest tests/ -v`
Expected: No errors, all tests pass

**Step 6: Commit**

```
git add resources/lib/data/storage.py tests/test_storage.py
git commit -m "feat: get_storage() clone fallback via advertised shared DB config"
```

---

### Task 5: Premiere filter resume check

**Files:**
- Modify: `resources/lib/playback/browse_mode.py:227-253`
- Test: `tests/test_browse_premiere_resume.py` (new)

**Step 1: Write failing tests**

Create `tests/test_browse_premiere_resume.py`:

```python
"""Tests for browse mode premiere filter with resume state awareness."""
import pytest


@pytest.fixture
def patch_window(mocker):
    """Patch WINDOW.getProperty to return controlled values."""
    mock_window = mocker.patch(
        'resources.lib.playback.browse_mode.WINDOW'
    )

    def setup(prop_map):
        """Set up window property values.

        Args:
            prop_map: dict of property_key -> value string
        """
        def get_prop(key):
            return prop_map.get(key, '')
        mock_window.getProperty.side_effect = get_prop

    return setup


class TestShouldIncludeResumeState:
    """Premiere filter should include in-progress premieres."""

    def _make_should_include(self, series_premieres, season_premieres):
        """Create should_include function with given premiere settings."""
        from resources.lib.constants import PREMIERE_ONLY, PREMIERE_SKIP
        from resources.lib.playback.browse_mode import WINDOW

        only_mode = (series_premieres == PREMIERE_ONLY
                     or season_premieres == PREMIERE_ONLY)

        class FakeConfig:
            pass
        config = FakeConfig()
        config.series_premieres = series_premieres
        config.season_premieres = season_premieres

        def should_include(show_entry):
            episode_no = WINDOW.getProperty(f"EasyTV.{show_entry[1]}.EpisodeNo")
            if not episode_no or len(episode_no) < 6:
                return not only_mode
            try:
                season_num = int(episode_no[1:3])
                episode_num = int(episode_no[4:6])
            except (ValueError, IndexError):
                return not only_mode

            is_premiere = (episode_num == 1)

            if is_premiere:
                resume = WINDOW.getProperty(f"EasyTV.{show_entry[1]}.Resume")
                if resume == "true":
                    return True

            if only_mode:
                if not is_premiere:
                    return False
                if season_num == 1 and config.series_premieres == PREMIERE_SKIP:
                    return False
                if season_num > 1 and config.season_premieres == PREMIERE_SKIP:
                    return False
                return True
            else:
                if not is_premiere:
                    return True
                if season_num == 1:
                    return config.series_premieres != PREMIERE_SKIP
                return config.season_premieres != PREMIERE_SKIP

        return should_include

    def test_season_premiere_with_resume_included(self, patch_window):
        """S02E01 with resume=true should be included even with SKIP."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'true',
        })
        should_include = self._make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 318, '5996']) is True

    def test_season_premiere_without_resume_excluded(self, patch_window):
        """S02E01 with resume=false should be excluded with SKIP."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'false',
        })
        should_include = self._make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 318, '5996']) is False

    def test_series_premiere_with_resume_included(self, patch_window):
        """S01E01 with resume=true should be included even with SKIP."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.100.EpisodeNo': 'S01E01',
            'EasyTV.100.Resume': 'true',
        })
        should_include = self._make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 100, '1234']) is True

    def test_non_premiere_unaffected(self, patch_window):
        """S02E17 should be included regardless of resume state."""
        from resources.lib.constants import PREMIERE_SKIP
        patch_window({
            'EasyTV.135.EpisodeNo': 'S02E17',
            'EasyTV.135.Resume': 'false',
        })
        should_include = self._make_should_include(PREMIERE_SKIP, PREMIERE_SKIP)
        assert should_include([0, 135, '6840']) is True

    def test_premiere_with_mix_in_unaffected(self, patch_window):
        """With MIX_IN, premieres are always included (resume irrelevant)."""
        from resources.lib.constants import PREMIERE_MIX_IN
        patch_window({
            'EasyTV.318.EpisodeNo': 'S02E01',
            'EasyTV.318.Resume': 'false',
        })
        should_include = self._make_should_include(PREMIERE_MIX_IN, PREMIERE_MIX_IN)
        assert should_include([0, 318, '5996']) is True
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_browse_premiere_resume.py -v`
Expected: `test_season_premiere_with_resume_included` and `test_series_premiere_with_resume_included` FAIL (resume check not implemented yet)

**Step 3: Implement the resume check**

In `browse_mode.py`, modify `should_include()` at line 238. After:

```python
        is_premiere = (episode_num == 1)
```

Add:

```python
        # In-progress premieres are always included (user is actively watching)
        if is_premiere:
            resume = WINDOW.getProperty(f"EasyTV.{show_entry[1]}.Resume")
            if resume == "true":
                return True
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_browse_premiere_resume.py -v`
Expected: All 6 PASS

**Step 5: Commit**

```
git add resources/lib/playback/browse_mode.py tests/test_browse_premiere_resume.py
git commit -m "fix: premiere filter includes in-progress episodes with resume point"
```

---

### Task 6: Diagnostic logging

**Files:**
- Modify: `resources/lib/playback/browse_mode.py:255-270`
- Modify: `resources/lib/playback/random_player.py:1128-1132`

**Step 1: Add premiere filter summary log**

In `browse_mode.py`, in `_fetch_data()`, replace line 266-267:

```python
        if needs_premiere_filter:
            show_data = [x for x in show_data if should_include(x)]
```

With:

```python
        if needs_premiere_filter:
            before_count = len(show_data)
            show_data = [x for x in show_data if should_include(x)]
            excluded = before_count - len(show_data)
            if excluded:
                log.debug("Premiere filter applied",
                          event="browse.premiere_filter",
                          before=before_count,
                          after=len(show_data),
                          excluded=excluded)
```

**Step 2: Add sync skip logging in browse_mode.py**

In `browse_mode.py`, replace lines 276-278:

```python
        storage = get_storage()
        if storage.needs_refresh():
            sync_show_list_from_shared_db(storage, log)
```

With:

```python
        storage = get_storage()
        if storage.needs_refresh():
            sync_show_list_from_shared_db(storage, log)
        else:
            log.debug("Skipping shared DB sync",
                      event="browse.sync_skip",
                      reason="not_stale" if hasattr(storage, '_db') else "local_storage")
```

**Step 3: Add sync skip logging in random_player.py**

In `random_player.py`, replace lines 1130-1132:

```python
                storage = get_storage()
                if storage.needs_refresh():
                    sync_show_list_from_shared_db(storage, log)
```

With:

```python
                storage = get_storage()
                if storage.needs_refresh():
                    sync_show_list_from_shared_db(storage, log)
                else:
                    log.debug("Skipping shared DB sync",
                              event="playlist.sync_skip",
                              reason="not_stale" if hasattr(storage, '_db') else "local_storage")
```

**Step 4: Run full validation**

Run:
```bash
find . -name "*.py" -not -path "*/__pycache__/*" \
  -exec python3 -m py_compile {} \; && \
echo "Syntax OK" && \
pyflakes $(find . -name "*.py" -not -path "*/__pycache__/*")
```
Expected: Syntax OK, no pyflakes errors

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass

**Step 5: Commit**

```
git add resources/lib/playback/browse_mode.py resources/lib/playback/random_player.py
git commit -m "fix: add diagnostic logging for premiere filter, sync decisions"
```

---

### Task 7: Final validation

**Step 1: Run pyright**

Run: `pyright`
Expected: No new errors (existing errors may be present)

**Step 2: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass

**Step 3: Run kodi-addon-checker**

Run: `kodi-addon-checker --branch omega .`
Expected: No new errors

**Step 4: Version bump**

Bump version in `addon.xml` to `1.5.2~alpha2`.

**Step 5: Commit**

```
git add addon.xml
git commit -m "chore: bump version to 1.5.2~alpha2"
```
