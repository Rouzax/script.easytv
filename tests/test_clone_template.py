"""Tests for resources/settings_clone.xml structural correctness.

Logging: none (pure XML parse, no runtime).
"""

import xml.etree.ElementTree as ET

TEMPLATE = "resources/settings_clone.xml"


def test_clone_template_is_valid_xml():
    ET.parse(TEMPLATE)  # raises on malformed


def test_clone_template_has_random_order_setting():
    root = ET.parse(TEMPLATE).getroot()
    ids = {s.get("id") for s in root.iter("setting")}
    assert {"random_order_shows", "select_random_order_shows",
            "random_order_shows_display"} <= ids


def test_random_order_lives_in_a_watch_order_group_under_shows():
    root = ET.parse(TEMPLATE).getroot()
    shows = next(c for c in root.iter("category") if c.get("id") == "shows")
    wo = next((g for g in shows.iter("group") if g.get("id") == "watch_order"), None)
    assert wo is not None, "watch_order group must be under the shows category"
    wo_ids = {s.get("id") for s in wo.iter("setting")}
    assert "select_random_order_shows" in wo_ids
    assert "random_order_shows_display" in wo_ids
