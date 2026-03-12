"""Tests for resources/lib/constants.py — PlaylistConfig XML generation."""
from resources.lib.constants import PLAYLIST_CONFIG


# ── XML Headers ──────────────────────────────────────────────────────

class TestPlaylistXmlHeaders:
    def test_episode_header_structure(self):
        h = PLAYLIST_CONFIG.episode_xml_header("Test Playlist")
        assert '<smartplaylist type="episodes">' in h
        assert '<name>Test Playlist</name>' in h
        assert '<match>one</match>' in h

    def test_tvshow_header_structure(self):
        h = PLAYLIST_CONFIG.tvshow_xml_header("My Shows")
        assert '<smartplaylist type="tvshows">' in h
        assert '<name>My Shows</name>' in h

    def test_header_escapes_ampersand(self):
        h = PLAYLIST_CONFIG.episode_xml_header("Tom & Jerry")
        assert "Tom &amp; Jerry" in h

    def test_header_escapes_angle_brackets(self):
        h = PLAYLIST_CONFIG.episode_xml_header("Show <Special>")
        assert "Show &lt;Special&gt;" in h

    def test_header_preserves_quotes(self):
        # xml.sax.saxutils.escape() does not escape quotes by default
        h = PLAYLIST_CONFIG.episode_xml_header('Show "Quoted"')
        assert 'Show "Quoted"' in h


# ── XML Entries ──────────────────────────────────────────────────────

class TestPlaylistXmlEntries:
    def test_episode_entry(self):
        e = PLAYLIST_CONFIG.episode_entry(123, "episode.mkv")
        assert '<!--123-->' in e
        assert '<rule field="filename" operator="is">' in e
        assert '<value>episode.mkv</value>' in e

    def test_tvshow_entry(self):
        e = PLAYLIST_CONFIG.tvshow_entry(456, "Breaking Bad")
        assert '<!--456-->' in e
        assert '<rule field="title" operator="is">' in e
        assert '<value>Breaking Bad</value>' in e

    def test_episode_entry_escapes_filename(self):
        e = PLAYLIST_CONFIG.episode_entry(1, "file&name<test>.mkv")
        assert "file&amp;name&lt;test&gt;.mkv" in e

    def test_tvshow_entry_escapes_title(self):
        e = PLAYLIST_CONFIG.tvshow_entry(1, "Tom & Jerry's <Show>")
        assert "Tom &amp; Jerry" in e
        assert "&lt;Show&gt;" in e


# ── Filename Lists ───────────────────────────────────────────────────

class TestPlaylistFilenames:
    def test_all_episode_filenames_count(self):
        assert len(PLAYLIST_CONFIG.all_episode_filenames()) == 5

    def test_all_tvshow_filenames_count(self):
        assert len(PLAYLIST_CONFIG.all_tvshow_filenames()) == 5

    def test_all_filenames_count(self):
        assert len(PLAYLIST_CONFIG.all_filenames()) == 10

    def test_all_filenames_contains_both(self):
        all_names = PLAYLIST_CONFIG.all_filenames()
        episode_names = PLAYLIST_CONFIG.all_episode_filenames()
        tvshow_names = PLAYLIST_CONFIG.all_tvshow_filenames()
        assert all_names == episode_names + tvshow_names

    def test_filenames_end_with_xsp(self):
        for fn in PLAYLIST_CONFIG.all_filenames():
            assert fn.endswith(".xsp"), f"{fn} doesn't end with .xsp"
