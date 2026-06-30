"""Tests for shared conversion utilities."""

from src.utils.converters import dict_to_dimensions, dict_to_env_vars, dict_to_tags


class TestDictToTags:
    def test_basic_conversion(self):
        result = dict_to_tags({"env": "prod", "team": "platform"})
        assert result == [
            {"key": "env", "value": "prod"},
            {"key": "team", "value": "platform"},
        ]

    def test_empty_dict(self):
        assert dict_to_tags({}) == []

    def test_single_tag(self):
        assert dict_to_tags({"k": "v"}) == [{"key": "k", "value": "v"}]


class TestDictToDimensions:
    def test_basic_conversion(self):
        result = dict_to_dimensions({"ServiceName": "my-svc"})
        assert result == [{"Name": "ServiceName", "Value": "my-svc"}]

    def test_empty_dict(self):
        assert dict_to_dimensions({}) == []

    def test_multiple_dimensions(self):
        result = dict_to_dimensions({"Cluster": "c1", "Service": "s1"})
        assert len(result) == 2


class TestDictToEnvVars:
    def test_basic_conversion(self):
        result = dict_to_env_vars({"ENV": "prod"})
        assert result == [{"name": "ENV", "value": "prod"}]

    def test_empty_dict(self):
        assert dict_to_env_vars({}) == []

    def test_non_string_values_converted(self):
        result = dict_to_env_vars({"PORT": 8080, "DEBUG": True})
        assert result == [
            {"name": "PORT", "value": "8080"},
            {"name": "DEBUG", "value": "True"},
        ]
