"""Tests for browse window art URL handling.

The skin's multiimage fanart panels (Big Screen, Posters) cannot consume
Kodi's image:// wrapped URLs in <imagepath>: the loader rejects them and
the panel stays black. The Fanart_Image list item property must therefore
carry the raw inner path, while setArt keeps the wrapped form (plain image
controls handle image:// fine).
"""
from resources.lib.ui.browse_window import _unwrap_image_url


class TestUnwrapImageUrl:
    def test_unwraps_smb_fanart_url(self):
        wrapped = (
            "image://smb%3a%2f%2fHYPERV%2fData%2fTVSeries%2fEN"
            "%2f1923%20(2022)%2ffanart.jpg/"
        )
        assert _unwrap_image_url(wrapped) == (
            "smb://HYPERV/Data/TVSeries/EN/1923 (2022)/fanart.jpg"
        )

    def test_unwraps_http_url(self):
        wrapped = (
            "image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2foriginal"
            "%2fabc.jpg/"
        )
        assert _unwrap_image_url(wrapped) == (
            "https://image.tmdb.org/t/p/original/abc.jpg"
        )

    def test_raw_path_passes_through(self):
        raw = "smb://HYPERV/Data/TVSeries/EN/1923 (2022)/fanart.jpg"
        assert _unwrap_image_url(raw) == raw

    def test_empty_value_passes_through(self):
        assert _unwrap_image_url("") == ""

    def test_wrapped_value_without_trailing_slash(self):
        wrapped = "image://smb%3a%2f%2fserver%2ffanart.jpg"
        assert _unwrap_image_url(wrapped) == "smb://server/fanart.jpg"
