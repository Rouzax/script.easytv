"""Tests for smart playlist file writing."""
import os
from unittest.mock import patch

from resources.lib.data import smart_playlists as sp


def _write(loc, show_id=439, value="Show/ep01.mkv"):
    """Write one episode entry to a Continue Watching playlist in loc."""
    with patch.object(sp, '_get_playlist_location', return_value=loc):
        return sp._write_show_to_playlist_file(
            "EasyTV - Episode - Continue Watching.xsp",
            "EasyTV - Episode - Continue Watching",
            show_id,
            value,
            "episode",
            quiet=True,
        )


class _WriteSpy:
    """Context manager that records write-mode open() calls."""

    def __init__(self):
        self.write_modes = []

    def __enter__(self):
        real_open = open

        def spy(path, mode='r', *args, **kwargs):
            if 'w' in mode or 'a' in mode:
                self.write_modes.append(mode)
            return real_open(path, mode, *args, **kwargs)

        self._patch = patch('builtins.open', spy)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        return False


class TestWriteContentCheck:
    """The writer must skip the rewrite when the file is already correct.

    This keeps a shared (UNC) playlist file safe: a consuming instance that
    computes the identical entry must not rewrite the file the producer
    already wrote, avoiding redundant writes and write races.
    """

    def test_skips_rewrite_when_content_identical(self, tmp_path):
        loc = str(tmp_path) + os.sep

        assert _write(loc) is True  # create

        with _WriteSpy() as spy:
            assert _write(loc) is True  # identical -> should skip write

        assert spy.write_modes == []

    def test_rewrites_when_content_differs(self, tmp_path):
        loc = str(tmp_path) + os.sep

        assert _write(loc, value="Show/ep01.mkv") is True

        with _WriteSpy() as spy:
            assert _write(loc, value="Show/ep02.mkv") is True  # changed -> write

        assert spy.write_modes != []
