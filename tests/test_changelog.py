"""
Tests for changelog.txt; the version history packaged into the addon zip.

changelog.txt ships to users and Kodi renders it, so a malformed section
header is user-visible. The v1.10.1 release wrote a placeholder over the
preceding header and shipped it, because the release checklist only
verifies the top entry against addon.xml and never looks further down.
These tests check every header, not just the newest one.
"""
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHANGELOG = os.path.join(REPO_ROOT, 'changelog.txt')

# Kodi-facing versions use a tilde for pre-releases: v1.4.0~alpha8 (2026-01-31)
HEADER_RE = re.compile(r'^v\d+\.\d+\.\d+(?:~[a-z]+\d*)? \(\d{4}-\d{2}-\d{2}\)$')


def _section_headers():
    """Return [(line_number, text)] for every line that underlines as a header.

    A section header is any line directly above a run of dashes. Bullet text
    is indented and never underlined, so this selects headers exactly.
    """
    with open(CHANGELOG, encoding='utf-8') as handle:
        lines = handle.read().splitlines()

    headers = []
    for index, line in enumerate(lines[:-1]):
        underline = lines[index + 1].strip()
        if underline and set(underline) == {'-'}:
            headers.append((index + 1, line.strip()))
    return headers


class TestChangelogHeaders:
    """Regression tests for changelog.txt section headers."""

    def test_changelog_exists(self):
        assert os.path.isfile(CHANGELOG), f"Changelog missing: {CHANGELOG}"

    def test_changelog_has_headers(self):
        """Guards the parser itself: no headers found means the format moved."""
        assert _section_headers(), (
            "No section headers found; the dashed-underline convention changed "
            "and this test no longer checks anything."
        )

    def test_every_header_is_well_formed(self):
        """Catches placeholders and hand-edited headers anywhere in the file."""
        malformed = [
            f"line {number}: {text!r}"
            for number, text in _section_headers()
            if not HEADER_RE.match(text)
        ]
        assert not malformed, (
            "changelog.txt section headers must read 'vX.Y.Z (YYYY-MM-DD)':\n  "
            + "\n  ".join(malformed)
        )

    def test_headers_are_unique(self):
        """A duplicated version usually means an entry was pasted, not moved."""
        versions = [text for _, text in _section_headers()]
        duplicates = {v for v in versions if versions.count(v) > 1}
        assert not duplicates, f"Duplicate changelog headers: {sorted(duplicates)}"
