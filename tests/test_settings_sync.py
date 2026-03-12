"""
Tests that settings_clone.xml stays in sync with settings.xml.

Catches drift between the two files: wrong category, mismatched attributes,
accidental omissions. Settings intentionally absent from clone are allowlisted.
"""
import os
from xml.etree import ElementTree as et
from typing import Dict, List, Set, Tuple

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAIN_SETTINGS = os.path.join(_ROOT, "resources", "settings.xml")
_CLONE_SETTINGS = os.path.join(_ROOT, "resources", "settings_clone.xml")

# ---------------------------------------------------------------------------
# Settings that are intentionally ONLY in main (service/admin features)
# ---------------------------------------------------------------------------
MAIN_ONLY_SETTINGS: Set[str] = {
    # Watch order (library-wide, managed by service)
    "select_random_order_shows",
    "random_order_shows_display",
    "random_order_shows",           # hidden
    # Specials inclusion (service-level)
    "include_positioned_specials",
    # Playback category (service monitors playback)
    "nextprompt",
    "nextprompt_in_playlist",
    "promptduration",
    "promptdefaultaction",
    "previous_episode_check",
    # Notifications (service-level)
    "notify",
    # Advanced service/admin tools
    "startup",
    "playlist_export_episodes",
    "playlist_export_tvshows",
    "smartplaylist_filter_enabled",
    "smartplaylist_filter_display",
    "multi_instance_sync",
    "clear_sync_data",
    "clone",
}

# Settings that are intentionally ONLY in clone
CLONE_ONLY_SETTINGS: Set[str] = {
    "first_run",    # clone-specific initialization flag
}

# Attributes to compare for shared settings
_SETTING_ATTRS = ("type",)

# Child elements to compare for shared settings
_SETTING_CHILDREN = ("level", "default")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_settings(path: str) -> Dict[str, dict]:
    """Parse a settings XML and return {setting_id: info_dict}."""
    tree = et.parse(path)
    settings = {}
    for cat in tree.findall(".//category"):
        cat_id = cat.get("id", "")
        for group in cat.findall(".//group"):
            group_id = group.get("id", "")
            for setting in group.findall("setting"):
                sid = setting.get("id")
                if sid is None:
                    continue
                settings[sid] = {
                    "category": cat_id,
                    "group": group_id,
                    "type": setting.get("type", ""),
                    "level": (setting.findtext("level") or "").strip(),
                    "default": (setting.findtext("default") or "").strip(),
                    "constraints": _extract_constraints(setting),
                    "options": _extract_options(setting),
                }
    return settings


def _extract_constraints(setting: et.Element) -> Dict[str, str]:
    """Extract min/max/step constraints."""
    result = {}
    constraints = setting.find("constraints")
    if constraints is not None:
        for tag in ("minimum", "maximum", "step"):
            elem = constraints.find(tag)
            if elem is not None and elem.text:
                result[tag] = elem.text.strip()
    return result


def _extract_options(setting: et.Element) -> List[Tuple[str, str]]:
    """Extract option label/value pairs."""
    options = []
    for opt in setting.findall(".//option"):
        label = opt.get("label", "")
        value = (opt.text or "").strip()
        options.append((label, value))
    return options


@pytest.fixture(scope="module")
def main_settings() -> Dict[str, dict]:
    return _parse_settings(_MAIN_SETTINGS)


@pytest.fixture(scope="module")
def clone_settings() -> Dict[str, dict]:
    return _parse_settings(_CLONE_SETTINGS)


@pytest.fixture(scope="module")
def shared_ids(main_settings, clone_settings) -> Set[str]:
    return set(main_settings.keys()) & set(clone_settings.keys())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestSettingsCompleteness:
    """Verify no settings are accidentally missing from clone."""

    def test_main_only_settings_are_allowlisted(self, main_settings, clone_settings):
        """Every setting in main but not clone must be in the allowlist."""
        main_only = set(main_settings.keys()) - set(clone_settings.keys())
        unexpected = main_only - MAIN_ONLY_SETTINGS
        assert not unexpected, (
            f"Settings in main but missing from clone (not allowlisted): "
            f"{sorted(unexpected)}\n"
            f"If intentional, add to MAIN_ONLY_SETTINGS in this test."
        )

    def test_clone_only_settings_are_allowlisted(self, main_settings, clone_settings):
        """Every setting in clone but not main must be in the allowlist."""
        clone_only = set(clone_settings.keys()) - set(main_settings.keys())
        unexpected = clone_only - CLONE_ONLY_SETTINGS
        assert not unexpected, (
            f"Settings in clone but missing from main (not allowlisted): "
            f"{sorted(unexpected)}\n"
            f"If intentional, add to CLONE_ONLY_SETTINGS in this test."
        )

    def test_allowlists_are_accurate(self, main_settings, clone_settings):
        """Allowlisted settings must actually exist in the expected file."""
        for sid in MAIN_ONLY_SETTINGS:
            assert sid in main_settings, (
                f"MAIN_ONLY_SETTINGS lists '{sid}' but it doesn't exist in settings.xml"
            )
        for sid in CLONE_ONLY_SETTINGS:
            assert sid in clone_settings, (
                f"CLONE_ONLY_SETTINGS lists '{sid}' but it doesn't exist in settings_clone.xml"
            )


class TestSettingsPlacement:
    """Verify shared settings are in the same category and group."""

    def test_shared_settings_same_category(self, main_settings, clone_settings, shared_ids):
        """Shared settings must be in the same category."""
        misplaced = []
        for sid in sorted(shared_ids):
            main_cat = main_settings[sid]["category"]
            clone_cat = clone_settings[sid]["category"]
            if main_cat != clone_cat:
                misplaced.append(
                    f"  {sid}: main={main_cat}, clone={clone_cat}"
                )
        assert not misplaced, (
            "Settings in different categories:\n" + "\n".join(misplaced)
        )

    def test_shared_settings_same_group(self, main_settings, clone_settings, shared_ids):
        """Shared settings must be in the same group."""
        misplaced = []
        for sid in sorted(shared_ids):
            main_grp = main_settings[sid]["group"]
            clone_grp = clone_settings[sid]["group"]
            if main_grp != clone_grp:
                misplaced.append(
                    f"  {sid}: main={main_grp}, clone={clone_grp}"
                )
        assert not misplaced, (
            "Settings in different groups:\n" + "\n".join(misplaced)
        )


class TestSettingsAttributes:
    """Verify shared settings have identical attributes."""

    def test_shared_settings_same_type(self, main_settings, clone_settings, shared_ids):
        """Setting type (boolean, integer, string, action) must match."""
        mismatched = []
        for sid in sorted(shared_ids):
            if main_settings[sid]["type"] != clone_settings[sid]["type"]:
                mismatched.append(
                    f"  {sid}: main={main_settings[sid]['type']}, "
                    f"clone={clone_settings[sid]['type']}"
                )
        assert not mismatched, (
            "Settings with different types:\n" + "\n".join(mismatched)
        )

    def test_shared_settings_same_level(self, main_settings, clone_settings, shared_ids):
        """Setting visibility level must match."""
        mismatched = []
        for sid in sorted(shared_ids):
            if main_settings[sid]["level"] != clone_settings[sid]["level"]:
                mismatched.append(
                    f"  {sid}: main={main_settings[sid]['level']}, "
                    f"clone={clone_settings[sid]['level']}"
                )
        assert not mismatched, (
            "Settings with different levels:\n" + "\n".join(mismatched)
        )

    def test_shared_settings_same_default(self, main_settings, clone_settings, shared_ids):
        """Default values must match."""
        mismatched = []
        for sid in sorted(shared_ids):
            if main_settings[sid]["default"] != clone_settings[sid]["default"]:
                mismatched.append(
                    f"  {sid}: main={main_settings[sid]['default']!r}, "
                    f"clone={clone_settings[sid]['default']!r}"
                )
        assert not mismatched, (
            "Settings with different defaults:\n" + "\n".join(mismatched)
        )

    def test_shared_settings_same_constraints(self, main_settings, clone_settings, shared_ids):
        """Constraints (min/max/step) must match."""
        mismatched = []
        for sid in sorted(shared_ids):
            main_c = main_settings[sid]["constraints"]
            clone_c = clone_settings[sid]["constraints"]
            if main_c != clone_c:
                mismatched.append(
                    f"  {sid}: main={main_c}, clone={clone_c}"
                )
        assert not mismatched, (
            "Settings with different constraints:\n" + "\n".join(mismatched)
        )

    def test_shared_settings_same_options(self, main_settings, clone_settings, shared_ids):
        """Option lists (spinner/select values) must match."""
        mismatched = []
        for sid in sorted(shared_ids):
            main_o = main_settings[sid]["options"]
            clone_o = clone_settings[sid]["options"]
            if main_o != clone_o:
                mismatched.append(
                    f"  {sid}: main={main_o}, clone={clone_o}"
                )
        assert not mismatched, (
            "Settings with different options:\n" + "\n".join(mismatched)
        )
