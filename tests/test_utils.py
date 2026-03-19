"""Tests for resources/lib/utils.py — core utilities."""
import pytest

from resources.lib.utils import (
    parse_version,
    compare_versions,
    sanitize_filename,
    runtime_converter,
    parse_lastplayed_date,
)


# ── parse_version ────────────────────────────────────────────────────

class TestParseVersion:
    def test_release(self):
        assert parse_version("1.2.3") == (1, 2, 3, 2, 0)

    def test_alpha(self):
        assert parse_version("1.2.3~alpha2") == (1, 2, 3, 0, 2)

    def test_beta(self):
        assert parse_version("1.2.3~beta1") == (1, 2, 3, 1, 1)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_version("not-a-version")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_version("")

    def test_ordering_alpha_lt_beta_lt_release(self):
        alpha = parse_version("1.0.0~alpha1")
        beta = parse_version("1.0.0~beta1")
        release = parse_version("1.0.0")
        assert alpha < beta < release

    def test_alpha_numbering(self):
        a1 = parse_version("1.0.0~alpha1")
        a2 = parse_version("1.0.0~alpha2")
        assert a1 < a2


# ── compare_versions ─────────────────────────────────────────────────

class TestCompareVersions:
    def test_equal(self):
        assert compare_versions("1.2.3", "1.2.3") == 0

    def test_greater(self):
        assert compare_versions("1.2.4", "1.2.3") == 1

    def test_less(self):
        assert compare_versions("1.2.3", "1.2.4") == -1

    def test_prerelease_less_than_release(self):
        assert compare_versions("1.2.3~beta1", "1.2.3") == -1

    def test_alpha_less_than_beta(self):
        assert compare_versions("1.2.3~alpha1", "1.2.3~beta1") == -1


# ── sanitize_filename ────────────────────────────────────────────────

class TestSanitizeFilename:
    def test_spaces_to_underscores(self):
        assert sanitize_filename("hello world") == "hello_world"

    def test_lowercased(self):
        assert sanitize_filename("HELLO") == "hello"

    def test_special_chars_removed(self):
        result = sanitize_filename("test!@#$%file")
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result

    def test_preserves_safe_chars(self):
        result = sanitize_filename("file-name_v1.0(beta)")
        assert result == "file-name_v1.0(beta)"

    def test_empty_input(self):
        assert sanitize_filename("") == ""

    def test_all_invalid(self):
        assert sanitize_filename("!!!") == ""

    def test_strips_whitespace(self):
        assert sanitize_filename("  test  ") == "test"


# ── runtime_converter ────────────────────────────────────────────────

class TestRuntimeConverter:
    def test_hhmmss(self):
        assert runtime_converter("1:30:00") == 5400

    def test_mmss(self):
        assert runtime_converter("45:30") == 2730

    def test_empty(self):
        assert runtime_converter("") == 0

    def test_invalid(self):
        assert runtime_converter("not-a-time") == 0

    def test_seconds_only(self):
        assert runtime_converter("120") == 120


# ── parse_lastplayed_date ────────────────────────────────────────────

class TestParseLastplayedDate:
    def test_valid_date(self):
        result = parse_lastplayed_date("2024-03-15 20:30:00")
        assert result > 0

    def test_empty_returns_zero(self):
        assert parse_lastplayed_date("") == 0.0

    def test_invalid_returns_zero(self):
        assert parse_lastplayed_date("not-a-date") == 0.0

    def test_none_returns_zero(self):
        # The function checks 'if not date_string' which handles None too
        assert parse_lastplayed_date(None) == 0.0


# ── invalidate_icon_cache ───────────────────────────────────────────

class TestInvalidateIconCache:
    """Tests for invalidate_icon_cache()."""

    def test_queries_textures_and_removes_each(self, mocker):
        """Cache invalidation should query matching textures then remove each."""
        mocker.patch('resources.lib.utils.xbmcaddon')
        mock_json = mocker.patch('resources.lib.utils.json_query')
        mock_json.return_value = {
            "textures": [
                {"textureid": 10},
                {"textureid": 20},
            ]
        }
        from resources.lib.utils import invalidate_icon_cache
        invalidate_icon_cache('script.easytv')

        # First call: GetTextures query
        get_call = mock_json.call_args_list[0]
        assert get_call[0][0]['method'] == 'Textures.GetTextures'
        assert get_call[0][0]['params']['filter']['value'] == 'script.easytv'

        # Subsequent calls: RemoveTexture for each ID
        remove_calls = mock_json.call_args_list[1:]
        assert len(remove_calls) == 2
        assert remove_calls[0][0][0]['params']['textureid'] == 10
        assert remove_calls[1][0][0]['params']['textureid'] == 20

    def test_no_textures_found(self, mocker):
        """No errors when texture cache has no matching entries."""
        mocker.patch('resources.lib.utils.xbmcaddon')
        mock_json = mocker.patch('resources.lib.utils.json_query')
        mock_json.return_value = {"textures": []}
        from resources.lib.utils import invalidate_icon_cache
        invalidate_icon_cache('script.easytv')
        assert mock_json.call_count == 1  # Only the GetTextures query
