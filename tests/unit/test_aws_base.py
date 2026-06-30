"""Tests for AWS base class and error handling utilities."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from src.utils.aws_base import AWSBaseManager, aws_api_call


class ConcreteManager(AWSBaseManager):
    _service_name = "ecs"

    @aws_api_call("create resource '{name}'")
    def create_resource(self, name):
        return self.client.create_resource(name=name)

    @aws_api_call("list resources")
    def list_resources(self):
        return self.client.list_resources()


class TestAWSBaseManager:
    def test_init_with_session(self):
        session = MagicMock()
        manager = ConcreteManager(region="us-west-2", session=session)
        session.client.assert_called_once_with("ecs", region_name="us-west-2")
        assert manager.region == "us-west-2"

    def test_init_default_region(self):
        session = MagicMock()
        manager = ConcreteManager(session=session)
        session.client.assert_called_once_with("ecs", region_name="us-east-1")
        assert manager.region == "us-east-1"

    def test_init_without_service_name_raises(self):
        class BadManager(AWSBaseManager):
            _service_name = ""

        with pytest.raises(ValueError, match="must set _service_name"):
            BadManager(session=MagicMock())


class TestAWSAPICallDecorator:
    def test_successful_call(self):
        session = MagicMock()
        manager = ConcreteManager(session=session)
        manager.client.create_resource.return_value = {"id": "123"}

        result = manager.create_resource("test")
        assert result == {"id": "123"}

    def test_client_error_wraps_as_runtime_error(self):
        session = MagicMock()
        manager = ConcreteManager(session=session)
        manager.client.create_resource.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "CreateResource",
        )

        with pytest.raises(RuntimeError, match="Failed to create resource 'test'"):
            manager.create_resource("test")

    def test_error_message_includes_param(self):
        session = MagicMock()
        manager = ConcreteManager(session=session)
        manager.client.create_resource.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "CreateResource",
        )

        with pytest.raises(RuntimeError, match="my-resource"):
            manager.create_resource("my-resource")

    def test_non_client_error_propagates(self):
        session = MagicMock()
        manager = ConcreteManager(session=session)
        manager.client.list_resources.side_effect = ValueError("unexpected")

        with pytest.raises(ValueError, match="unexpected"):
            manager.list_resources()
