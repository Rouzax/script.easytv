"""Tests for resources/lib/service/settings.py — _parse_show_setting."""
from resources.lib.service.settings import _parse_show_setting


class TestParseShowSetting:
    def test_new_dict_format(self):
        result, needs_migration = _parse_show_setting("{'367': 'The Alienist'}")
        assert result == {"367": "The Alienist"}
        assert needs_migration is False

    def test_old_list_format(self):
        result, needs_migration = _parse_show_setting("[367, 42]")
        assert result == {"367": "", "42": ""}
        assert needs_migration is True

    def test_empty_string(self):
        result, needs_migration = _parse_show_setting("")
        assert result == {}
        assert needs_migration is False

    def test_empty_list(self):
        result, needs_migration = _parse_show_setting("[]")
        assert result == {}
        assert needs_migration is False

    def test_empty_dict(self):
        result, needs_migration = _parse_show_setting("{}")
        assert result == {}
        assert needs_migration is False

    def test_none_string(self):
        result, needs_migration = _parse_show_setting("none")
        assert result == {}
        assert needs_migration is False

    def test_invalid_syntax(self):
        result, needs_migration = _parse_show_setting("not valid python")
        assert result == {}
        assert needs_migration is False

    def test_dict_keys_become_strings(self):
        result, _ = _parse_show_setting("{367: 'Show A', 42: 'Show B'}")
        assert "367" in result
        assert "42" in result

    def test_multiple_shows_dict(self):
        result, needs_migration = _parse_show_setting(
            "{'100': 'Show A', '200': 'Show B', '300': 'Show C'}"
        )
        assert len(result) == 3
        assert needs_migration is False
