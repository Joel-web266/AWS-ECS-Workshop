"""Base class and utilities for AWS service managers."""

import functools

import boto3
from botocore.exceptions import ClientError


class AWSBaseManager:
    """Base class for AWS service managers with shared client initialization."""

    _service_name: str = ""

    def __init__(self, region="us-east-1", session=None):
        if not self._service_name:
            raise ValueError("Subclasses must set _service_name")
        if session:
            self.client = session.client(self._service_name, region_name=region)
        else:
            self.client = boto3.client(self._service_name, region_name=region)
        self.region = region


def aws_api_call(operation_desc):
    """Decorator that wraps AWS API calls with consistent error handling.

    Catches ``ClientError`` and re-raises as ``RuntimeError`` with a
    descriptive message built from *operation_desc*.

    Usage::

        @aws_api_call("create cluster '{cluster_name}'")
        def create_cluster(self, cluster_name, ...):
            ...

    The format string is evaluated against the function's bound arguments so
    you can reference parameter names directly.
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except ClientError as e:
                import inspect

                sig = inspect.signature(fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                desc = operation_desc.format(**bound.arguments)
                raise RuntimeError(f"Failed to {desc}: {e}") from e

        return wrapper

    return decorator
