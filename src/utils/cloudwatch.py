"""CloudWatch logging and metrics utilities."""

from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


class CloudWatchManager:
    def __init__(self, region="us-east-1", session=None):
        if session:
            self.logs_client = session.client("logs", region_name=region)
            self.cw_client = session.client("cloudwatch", region_name=region)
        else:
            self.logs_client = boto3.client("logs", region_name=region)
            self.cw_client = boto3.client("cloudwatch", region_name=region)
        self.region = region

    def create_log_group(self, log_group_name, retention_days=30, tags=None):
        valid_retention = {
            1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365,
            400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653,
        }
        if retention_days not in valid_retention:
            raise ValueError(
                f"Invalid retention period: {retention_days}. "
                f"Must be one of: {sorted(valid_retention)}"
            )
        try:
            params = {"logGroupName": log_group_name}
            if tags:
                params["tags"] = tags
            self.logs_client.create_log_group(**params)
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                raise RuntimeError(
                    f"Failed to create log group '{log_group_name}': {e}"
                ) from e

        try:
            self.logs_client.put_retention_policy(
                logGroupName=log_group_name, retentionInDays=retention_days
            )
        except ClientError as e:
            raise RuntimeError(
                f"Failed to set retention policy on log group '{log_group_name}': {e}"
            ) from e
        return True

    def delete_log_group(self, log_group_name):
        try:
            self.logs_client.delete_log_group(logGroupName=log_group_name)
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to delete log group '{log_group_name}': {e}") from e

    def get_log_events(self, log_group_name, log_stream_name, limit=100):
        try:
            response = self.logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                limit=limit,
                startFromHead=True,
            )
            return response.get("events", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to get log events: {e}") from e

    def list_log_groups(self, prefix=None):
        try:
            params = {}
            if prefix:
                params["logGroupNamePrefix"] = prefix
            response = self.logs_client.describe_log_groups(**params)
            return response.get("logGroups", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list log groups: {e}") from e

    def list_log_streams(self, log_group_name, order_by="LastEventTime", limit=50):
        valid_orders = {"LogStreamName", "LastEventTime"}
        if order_by not in valid_orders:
            raise ValueError(f"Invalid order_by: {order_by}. Must be one of: {valid_orders}")
        try:
            response = self.logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy=order_by,
                descending=True,
                limit=limit,
            )
            return response.get("logStreams", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list log streams: {e}") from e

    def put_metric(self, namespace, metric_name, value, unit="None", dimensions=None):
        valid_units = {
            "Seconds", "Microseconds", "Milliseconds", "Bytes", "Kilobytes",
            "Megabytes", "Gigabytes", "Terabytes", "Bits", "Kilobits", "Megabits",
            "Gigabits", "Terabits", "Percent", "Count", "Bytes/Second",
            "Kilobytes/Second", "Megabytes/Second", "Gigabytes/Second",
            "Terabytes/Second", "Bits/Second", "Kilobits/Second", "Megabits/Second",
            "Gigabits/Second", "Terabits/Second", "Count/Second", "None",
        }
        if unit not in valid_units:
            raise ValueError(f"Invalid unit: {unit}")

        metric_data = {
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
            "Timestamp": datetime.now(timezone.utc),
        }
        if dimensions:
            metric_data["Dimensions"] = [
                {"Name": k, "Value": v} for k, v in dimensions.items()
            ]
        try:
            self.cw_client.put_metric_data(
                Namespace=namespace, MetricData=[metric_data]
            )
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to put metric '{metric_name}': {e}") from e

    def create_alarm(
        self, alarm_name, namespace, metric_name, threshold,
        comparison="GreaterThanThreshold", period=300, evaluation_periods=1,
        statistic="Average", actions=None, dimensions=None,
    ):
        valid_comparisons = {
            "GreaterThanThreshold",
            "GreaterThanOrEqualToThreshold",
            "LessThanThreshold",
            "LessThanOrEqualToThreshold",
        }
        if comparison not in valid_comparisons:
            raise ValueError(f"Invalid comparison: {comparison}")

        params = {
            "AlarmName": alarm_name,
            "Namespace": namespace,
            "MetricName": metric_name,
            "Threshold": threshold,
            "ComparisonOperator": comparison,
            "Period": period,
            "EvaluationPeriods": evaluation_periods,
            "Statistic": statistic,
        }
        if actions:
            params["AlarmActions"] = actions
        if dimensions:
            params["Dimensions"] = [
                {"Name": k, "Value": v} for k, v in dimensions.items()
            ]
        try:
            self.cw_client.put_metric_alarm(**params)
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to create alarm '{alarm_name}': {e}") from e

    def describe_alarms(self, alarm_names=None):
        try:
            params = {}
            if alarm_names:
                params["AlarmNames"] = alarm_names
            response = self.cw_client.describe_alarms(**params)
            return response.get("MetricAlarms", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to describe alarms: {e}") from e

    def delete_alarms(self, alarm_names):
        try:
            self.cw_client.delete_alarms(AlarmNames=alarm_names)
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to delete alarms: {e}") from e

    def get_ecs_log_config(self, log_group_name, stream_prefix="ecs"):
        return {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": log_group_name,
                "awslogs-region": self.region,
                "awslogs-stream-prefix": stream_prefix,
            },
        }
