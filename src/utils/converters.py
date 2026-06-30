"""Shared conversion utilities for AWS API data formats."""


def dict_to_tags(d):
    """Convert ``{"key": "value"}`` to ``[{"key": k, "value": v}, ...]``."""
    return [{"key": k, "value": v} for k, v in d.items()]


def dict_to_dimensions(d):
    """Convert ``{"Name": "Value"}`` to ``[{"Name": k, "Value": v}, ...]``."""
    return [{"Name": k, "Value": v} for k, v in d.items()]


def dict_to_env_vars(d):
    """Convert ``{"VAR": "val"}`` to ``[{"name": "VAR", "value": "val"}, ...]``."""
    return [{"name": k, "value": str(v)} for k, v in d.items()]
