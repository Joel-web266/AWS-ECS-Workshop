"""Tests for CloudWatch manager utilities."""

import pytest
from botocore.exceptions import ClientError

from src.utils.cloudwatch import CloudWatchManager


@pytest.fixture
def cw_manager(mock_session):
    return CloudWatchManager(region="us-east-1", session=mock_session)


class TestCreateLogGroup:
    def test_create_log_group(self, cw_manager):
        cw_manager.logs_client.create_log_group.return_value = {}
        cw_manager.logs_client.put_retention_policy.return_value = {}
        result = cw_manager.create_log_group("/ecs/workshop")
        assert result is True

    def test_create_log_group_with_tags(self, cw_manager):
        cw_manager.logs_client.create_log_group.return_value = {}
        cw_manager.logs_client.put_retention_policy.return_value = {}
        cw_manager.create_log_group("/ecs/workshop", tags={"env": "dev"})
        call_kwargs = cw_manager.logs_client.create_log_group.call_args[1]
        assert call_kwargs["tags"] == {"env": "dev"}

    def test_create_log_group_custom_retention(self, cw_manager):
        cw_manager.logs_client.create_log_group.return_value = {}
        cw_manager.logs_client.put_retention_policy.return_value = {}
        cw_manager.create_log_group("/ecs/workshop", retention_days=90)
        call_kwargs = cw_manager.logs_client.put_retention_policy.call_args[1]
        assert call_kwargs["retentionInDays"] == 90

    def test_create_log_group_invalid_retention(self, cw_manager):
        with pytest.raises(ValueError, match="Invalid retention period"):
            cw_manager.create_log_group("/ecs/workshop", retention_days=15)

    def test_create_log_group_already_exists(self, cw_manager):
        cw_manager.logs_client.create_log_group.side_effect = ClientError(
            {"Error": {"Code": "ResourceAlreadyExistsException", "Message": "exists"}},
            "CreateLogGroup",
        )
        result = cw_manager.create_log_group("/ecs/workshop")
        assert result is True

    def test_create_log_group_error(self, cw_manager):
        cw_manager.logs_client.create_log_group.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailableException", "Message": "fail"}},
            "CreateLogGroup",
        )
        with pytest.raises(RuntimeError, match="Failed to create log group"):
            cw_manager.create_log_group("/ecs/workshop")


class TestDeleteLogGroup:
    def test_delete_log_group(self, cw_manager):
        cw_manager.logs_client.delete_log_group.return_value = {}
        result = cw_manager.delete_log_group("/ecs/workshop")
        assert result is True

    def test_delete_log_group_error(self, cw_manager):
        cw_manager.logs_client.delete_log_group.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "nope"}},
            "DeleteLogGroup",
        )
        with pytest.raises(RuntimeError, match="Failed to delete log group"):
            cw_manager.delete_log_group("/ecs/workshop")


class TestGetLogEvents:
    def test_get_log_events(self, cw_manager):
        cw_manager.logs_client.get_log_events.return_value = {
            "events": [
                {"timestamp": 1234567890, "message": "Hello"},
                {"timestamp": 1234567891, "message": "World"},
            ]
        }
        result = cw_manager.get_log_events("/ecs/workshop", "stream-1")
        assert len(result) == 2

    def test_get_log_events_error(self, cw_manager):
        cw_manager.logs_client.get_log_events.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "nope"}},
            "GetLogEvents",
        )
        with pytest.raises(RuntimeError, match="Failed to get log events"):
            cw_manager.get_log_events("/ecs/workshop", "stream-1")


class TestListLogGroups:
    def test_list_log_groups(self, cw_manager):
        cw_manager.logs_client.describe_log_groups.return_value = {
            "logGroups": [{"logGroupName": "/ecs/workshop"}]
        }
        result = cw_manager.list_log_groups()
        assert len(result) == 1

    def test_list_log_groups_with_prefix(self, cw_manager):
        cw_manager.logs_client.describe_log_groups.return_value = {"logGroups": []}
        cw_manager.list_log_groups(prefix="/ecs")
        call_kwargs = cw_manager.logs_client.describe_log_groups.call_args[1]
        assert call_kwargs["logGroupNamePrefix"] == "/ecs"

    def test_list_log_groups_error(self, cw_manager):
        cw_manager.logs_client.describe_log_groups.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailableException", "Message": "fail"}},
            "DescribeLogGroups",
        )
        with pytest.raises(RuntimeError, match="Failed to list log groups"):
            cw_manager.list_log_groups()


class TestListLogStreams:
    def test_list_log_streams(self, cw_manager):
        cw_manager.logs_client.describe_log_streams.return_value = {
            "logStreams": [{"logStreamName": "stream-1"}]
        }
        result = cw_manager.list_log_streams("/ecs/workshop")
        assert len(result) == 1

    def test_list_log_streams_invalid_order(self, cw_manager):
        with pytest.raises(ValueError, match="Invalid order_by"):
            cw_manager.list_log_streams("/ecs/workshop", order_by="InvalidOrder")

    def test_list_log_streams_error(self, cw_manager):
        cw_manager.logs_client.describe_log_streams.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "nope"}},
            "DescribeLogStreams",
        )
        with pytest.raises(RuntimeError, match="Failed to list log streams"):
            cw_manager.list_log_streams("/ecs/workshop")


class TestPutMetric:
    def test_put_metric(self, cw_manager):
        cw_manager.cw_client.put_metric_data.return_value = {}
        result = cw_manager.put_metric("ECS/Workshop", "RequestCount", 42.0)
        assert result is True

    def test_put_metric_with_dimensions(self, cw_manager):
        cw_manager.cw_client.put_metric_data.return_value = {}
        cw_manager.put_metric(
            "ECS/Workshop", "CPUUtilization", 75.5,
            unit="Percent", dimensions={"ServiceName": "my-svc"}
        )
        call_kwargs = cw_manager.cw_client.put_metric_data.call_args[1]
        metric = call_kwargs["MetricData"][0]
        assert metric["Unit"] == "Percent"
        assert metric["Dimensions"] == [{"Name": "ServiceName", "Value": "my-svc"}]

    def test_put_metric_invalid_unit(self, cw_manager):
        with pytest.raises(ValueError, match="Invalid unit"):
            cw_manager.put_metric("ECS/Workshop", "Test", 1.0, unit="InvalidUnit")

    def test_put_metric_error(self, cw_manager):
        cw_manager.cw_client.put_metric_data.side_effect = ClientError(
            {"Error": {"Code": "InternalServiceFault", "Message": "fail"}},
            "PutMetricData",
        )
        with pytest.raises(RuntimeError, match="Failed to put metric"):
            cw_manager.put_metric("ECS/Workshop", "Test", 1.0)


class TestCreateAlarm:
    def test_create_alarm(self, cw_manager):
        cw_manager.cw_client.put_metric_alarm.return_value = {}
        result = cw_manager.create_alarm(
            "HighCPU", "AWS/ECS", "CPUUtilization", 80.0
        )
        assert result is True

    def test_create_alarm_with_actions_and_dimensions(self, cw_manager):
        cw_manager.cw_client.put_metric_alarm.return_value = {}
        cw_manager.create_alarm(
            "HighCPU", "AWS/ECS", "CPUUtilization", 80.0,
            actions=["arn:aws:sns:us-east-1:123:alert"],
            dimensions={"ServiceName": "my-svc"},
        )
        call_kwargs = cw_manager.cw_client.put_metric_alarm.call_args[1]
        assert call_kwargs["AlarmActions"] == ["arn:aws:sns:us-east-1:123:alert"]
        assert call_kwargs["Dimensions"] == [{"Name": "ServiceName", "Value": "my-svc"}]

    def test_create_alarm_invalid_comparison(self, cw_manager):
        with pytest.raises(ValueError, match="Invalid comparison"):
            cw_manager.create_alarm(
                "Bad", "AWS/ECS", "CPUUtilization", 80.0,
                comparison="InvalidComparison",
            )

    def test_create_alarm_error(self, cw_manager):
        cw_manager.cw_client.put_metric_alarm.side_effect = ClientError(
            {"Error": {"Code": "LimitExceededException", "Message": "limit"}},
            "PutMetricAlarm",
        )
        with pytest.raises(RuntimeError, match="Failed to create alarm"):
            cw_manager.create_alarm("Bad", "AWS/ECS", "CPUUtilization", 80.0)


class TestDescribeAlarms:
    def test_describe_alarms(self, cw_manager):
        cw_manager.cw_client.describe_alarms.return_value = {
            "MetricAlarms": [{"AlarmName": "HighCPU"}]
        }
        result = cw_manager.describe_alarms()
        assert len(result) == 1

    def test_describe_alarms_by_name(self, cw_manager):
        cw_manager.cw_client.describe_alarms.return_value = {"MetricAlarms": []}
        cw_manager.describe_alarms(alarm_names=["HighCPU"])
        call_kwargs = cw_manager.cw_client.describe_alarms.call_args[1]
        assert call_kwargs["AlarmNames"] == ["HighCPU"]

    def test_describe_alarms_error(self, cw_manager):
        cw_manager.cw_client.describe_alarms.side_effect = ClientError(
            {"Error": {"Code": "InternalServiceFault", "Message": "fail"}},
            "DescribeAlarms",
        )
        with pytest.raises(RuntimeError, match="Failed to describe alarms"):
            cw_manager.describe_alarms()


class TestDeleteAlarms:
    def test_delete_alarms(self, cw_manager):
        cw_manager.cw_client.delete_alarms.return_value = {}
        result = cw_manager.delete_alarms(["HighCPU"])
        assert result is True

    def test_delete_alarms_error(self, cw_manager):
        cw_manager.cw_client.delete_alarms.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "nope"}},
            "DeleteAlarms",
        )
        with pytest.raises(RuntimeError, match="Failed to delete alarms"):
            cw_manager.delete_alarms(["nonexistent"])


class TestGetECSLogConfig:
    def test_default_config(self, cw_manager):
        config = cw_manager.get_ecs_log_config("/ecs/workshop")
        assert config["logDriver"] == "awslogs"
        assert config["options"]["awslogs-group"] == "/ecs/workshop"
        assert config["options"]["awslogs-region"] == "us-east-1"
        assert config["options"]["awslogs-stream-prefix"] == "ecs"

    def test_custom_prefix(self, cw_manager):
        config = cw_manager.get_ecs_log_config("/ecs/workshop", stream_prefix="app")
        assert config["options"]["awslogs-stream-prefix"] == "app"
