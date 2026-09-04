"""Tests for guided-flow answer persistence."""
from resources.lib.data.storage import _read_json_file, _write_json_file


class TestJsonRoundTrip:
    def test_round_trip(self, tmp_path):
        path = str(tmp_path / "wizard_answers.json")
        data = {"genre": ["Comedy"], "depth": 10,
                "length": {"min": 0, "max": 30}}
        assert _write_json_file(path, data) is True
        assert _read_json_file(path) == data

    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert _read_json_file(str(tmp_path / "nope.json")) == {}

    def test_corrupt_file_returns_empty_dict(self, tmp_path):
        path = str(tmp_path / "bad.json")
        with open(path, "w") as fh:
            fh.write("{not json")
        assert _read_json_file(path) == {}

    def test_write_failure_returns_false(self, tmp_path):
        path = str(tmp_path / "no_such_dir" / "x.json")
        assert _write_json_file(path, {"a": 1}) is False

    def test_non_dict_content_returns_empty_dict(self, tmp_path):
        path = str(tmp_path / "list.json")
        with open(path, "w") as fh:
            fh.write("[1, 2]")
        assert _read_json_file(path) == {}
