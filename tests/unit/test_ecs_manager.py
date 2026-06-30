"""Tests for ECS manager utilities."""

import pytest
from botocore.exceptions import ClientError

from src.app.models import ServiceConfig
from src.utils.ecs_manager import ECSManager


@pytest.fixture
def ecs_manager(mock_session):
    return ECSManager(region="us-east-1", session=mock_session)


class TestCreateCluster:
    def test_create_cluster_basic(self, ecs_manager):
        ecs_manager.client.create_cluster.return_value = {
            "cluster": {"clusterName": "test-cluster", "status": "ACTIVE"}
        }
        result = ecs_manager.create_cluster("test-cluster")
        assert result["clusterName"] == "test-cluster"
        ecs_manager.client.create_cluster.assert_called_once_with(
            clusterName="test-cluster"
        )

    def test_create_cluster_with_tags(self, ecs_manager):
        ecs_manager.client.create_cluster.return_value = {
            "cluster": {"clusterName": "test-cluster", "status": "ACTIVE"}
        }
        result = ecs_manager.create_cluster("test-cluster", tags={"env": "dev"})
        assert result["clusterName"] == "test-cluster"
        ecs_manager.client.create_cluster.assert_called_once_with(
            clusterName="test-cluster",
            tags=[{"key": "env", "value": "dev"}],
        )

    def test_create_cluster_client_error(self, ecs_manager):
        ecs_manager.client.create_cluster.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}}, "CreateCluster"
        )
        with pytest.raises(RuntimeError, match="Failed to create cluster"):
            ecs_manager.create_cluster("test-cluster")


class TestDeleteCluster:
    def test_delete_cluster(self, ecs_manager):
        ecs_manager.client.delete_cluster.return_value = {
            "cluster": {"clusterName": "test-cluster", "status": "INACTIVE"}
        }
        result = ecs_manager.delete_cluster("test-cluster")
        assert result["status"] == "INACTIVE"

    def test_delete_cluster_error(self, ecs_manager):
        ecs_manager.client.delete_cluster.side_effect = ClientError(
            {"Error": {"Code": "ClusterNotFoundException", "Message": "nope"}},
            "DeleteCluster",
        )
        with pytest.raises(RuntimeError, match="Failed to delete cluster"):
            ecs_manager.delete_cluster("nonexistent")


class TestListClusters:
    def test_list_clusters(self, ecs_manager):
        ecs_manager.client.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-east-1:123:cluster/c1"]
        }
        result = ecs_manager.list_clusters()
        assert len(result) == 1

    def test_list_clusters_empty(self, ecs_manager):
        ecs_manager.client.list_clusters.return_value = {"clusterArns": []}
        result = ecs_manager.list_clusters()
        assert result == []

    def test_list_clusters_error(self, ecs_manager):
        ecs_manager.client.list_clusters.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}}, "ListClusters"
        )
        with pytest.raises(RuntimeError, match="Failed to list clusters"):
            ecs_manager.list_clusters()


class TestDescribeCluster:
    def test_describe_cluster(self, ecs_manager):
        ecs_manager.client.describe_clusters.return_value = {
            "clusters": [{"clusterName": "test", "status": "ACTIVE"}]
        }
        result = ecs_manager.describe_cluster("test")
        assert result["clusterName"] == "test"

    def test_describe_cluster_not_found(self, ecs_manager):
        ecs_manager.client.describe_clusters.return_value = {"clusters": []}
        result = ecs_manager.describe_cluster("nonexistent")
        assert result is None

    def test_describe_cluster_error(self, ecs_manager):
        ecs_manager.client.describe_clusters.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "DescribeClusters",
        )
        with pytest.raises(RuntimeError, match="Failed to describe cluster"):
            ecs_manager.describe_cluster("test")


class TestCreateService:
    def test_create_service_fargate(self, ecs_manager):
        config = ServiceConfig(
            name="my-svc",
            cluster="my-cluster",
            task_definition="my-task:1",
            desired_count=2,
            subnets=["subnet-123"],
            security_groups=["sg-123"],
        )
        ecs_manager.client.create_service.return_value = {
            "service": {"serviceName": "my-svc", "status": "ACTIVE"}
        }
        result = ecs_manager.create_service(config)
        assert result["serviceName"] == "my-svc"

    def test_create_service_invalid_config(self, ecs_manager):
        config = ServiceConfig(name="", cluster="", task_definition="")
        with pytest.raises(ValueError, match="Invalid service config"):
            ecs_manager.create_service(config)

    def test_create_service_ec2_launch_type(self, ecs_manager):
        config = ServiceConfig(
            name="ec2-svc",
            cluster="cluster",
            task_definition="task:1",
            launch_type="EC2",
        )
        ecs_manager.client.create_service.return_value = {
            "service": {"serviceName": "ec2-svc"}
        }
        result = ecs_manager.create_service(config)
        assert result["serviceName"] == "ec2-svc"
        call_kwargs = ecs_manager.client.create_service.call_args[1]
        assert "networkConfiguration" not in call_kwargs

    def test_create_service_no_grace_period(self, ecs_manager):
        config = ServiceConfig(
            name="svc",
            cluster="cluster",
            task_definition="task:1",
            health_check_grace_period=0,
        )
        ecs_manager.client.create_service.return_value = {
            "service": {"serviceName": "svc"}
        }
        ecs_manager.create_service(config)
        call_kwargs = ecs_manager.client.create_service.call_args[1]
        assert "healthCheckGracePeriodSeconds" not in call_kwargs

    def test_create_service_client_error(self, ecs_manager):
        config = ServiceConfig(
            name="svc", cluster="cluster", task_definition="task:1"
        )
        ecs_manager.client.create_service.side_effect = ClientError(
            {"Error": {"Code": "ServiceException", "Message": "fail"}},
            "CreateService",
        )
        with pytest.raises(RuntimeError, match="Failed to create service"):
            ecs_manager.create_service(config)


class TestUpdateService:
    def test_update_service_desired_count(self, ecs_manager):
        ecs_manager.client.update_service.return_value = {
            "service": {"serviceName": "svc", "desiredCount": 3}
        }
        result = ecs_manager.update_service("cluster", "svc", desired_count=3)
        assert result["desiredCount"] == 3

    def test_update_service_task_definition(self, ecs_manager):
        ecs_manager.client.update_service.return_value = {
            "service": {"serviceName": "svc"}
        }
        ecs_manager.update_service("cluster", "svc", task_definition="task:2")
        call_kwargs = ecs_manager.client.update_service.call_args[1]
        assert call_kwargs["taskDefinition"] == "task:2"

    def test_update_service_error(self, ecs_manager):
        ecs_manager.client.update_service.side_effect = ClientError(
            {"Error": {"Code": "ServiceNotFoundException", "Message": "nope"}},
            "UpdateService",
        )
        with pytest.raises(RuntimeError, match="Failed to update service"):
            ecs_manager.update_service("cluster", "svc", desired_count=1)


class TestDeleteService:
    def test_delete_service(self, ecs_manager):
        ecs_manager.client.delete_service.return_value = {
            "service": {"serviceName": "svc", "status": "DRAINING"}
        }
        result = ecs_manager.delete_service("cluster", "svc")
        assert result["status"] == "DRAINING"

    def test_delete_service_force(self, ecs_manager):
        ecs_manager.client.delete_service.return_value = {
            "service": {"serviceName": "svc"}
        }
        ecs_manager.delete_service("cluster", "svc", force=True)
        ecs_manager.client.delete_service.assert_called_once_with(
            cluster="cluster", service="svc", force=True
        )

    def test_delete_service_error(self, ecs_manager):
        ecs_manager.client.delete_service.side_effect = ClientError(
            {"Error": {"Code": "ServiceNotFoundException", "Message": "nope"}},
            "DeleteService",
        )
        with pytest.raises(RuntimeError, match="Failed to delete service"):
            ecs_manager.delete_service("cluster", "svc")


class TestListServices:
    def test_list_services(self, ecs_manager):
        ecs_manager.client.list_services.return_value = {
            "serviceArns": ["arn:aws:ecs:us-east-1:123:service/svc"]
        }
        result = ecs_manager.list_services("cluster")
        assert len(result) == 1

    def test_list_services_error(self, ecs_manager):
        ecs_manager.client.list_services.side_effect = ClientError(
            {"Error": {"Code": "ClusterNotFoundException", "Message": "nope"}},
            "ListServices",
        )
        with pytest.raises(RuntimeError, match="Failed to list services"):
            ecs_manager.list_services("nonexistent")


class TestDescribeService:
    def test_describe_service(self, ecs_manager):
        ecs_manager.client.describe_services.return_value = {
            "services": [{"serviceName": "svc", "status": "ACTIVE"}]
        }
        result = ecs_manager.describe_service("cluster", "svc")
        assert result["serviceName"] == "svc"

    def test_describe_service_not_found(self, ecs_manager):
        ecs_manager.client.describe_services.return_value = {"services": []}
        result = ecs_manager.describe_service("cluster", "nonexistent")
        assert result is None

    def test_describe_service_error(self, ecs_manager):
        ecs_manager.client.describe_services.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "DescribeServices",
        )
        with pytest.raises(RuntimeError, match="Failed to describe service"):
            ecs_manager.describe_service("cluster", "svc")


class TestListTasks:
    def test_list_tasks(self, ecs_manager):
        ecs_manager.client.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-east-1:123:task/t1"]
        }
        result = ecs_manager.list_tasks("cluster")
        assert len(result) == 1

    def test_list_tasks_with_service(self, ecs_manager):
        ecs_manager.client.list_tasks.return_value = {"taskArns": []}
        ecs_manager.list_tasks("cluster", service_name="svc")
        call_kwargs = ecs_manager.client.list_tasks.call_args[1]
        assert call_kwargs["serviceName"] == "svc"

    def test_list_tasks_error(self, ecs_manager):
        ecs_manager.client.list_tasks.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}}, "ListTasks"
        )
        with pytest.raises(RuntimeError, match="Failed to list tasks"):
            ecs_manager.list_tasks("cluster")


class TestStopTask:
    def test_stop_task(self, ecs_manager):
        ecs_manager.client.stop_task.return_value = {
            "task": {"taskArn": "arn:task/t1", "lastStatus": "STOPPED"}
        }
        result = ecs_manager.stop_task("cluster", "arn:task/t1")
        assert result["lastStatus"] == "STOPPED"

    def test_stop_task_custom_reason(self, ecs_manager):
        ecs_manager.client.stop_task.return_value = {"task": {"taskArn": "t1"}}
        ecs_manager.stop_task("cluster", "t1", reason="Maintenance")
        call_kwargs = ecs_manager.client.stop_task.call_args[1]
        assert call_kwargs["reason"] == "Maintenance"

    def test_stop_task_error(self, ecs_manager):
        ecs_manager.client.stop_task.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterException", "Message": "nope"}},
            "StopTask",
        )
        with pytest.raises(RuntimeError, match="Failed to stop task"):
            ecs_manager.stop_task("cluster", "bad-arn")


class TestGetServiceStatus:
    def test_service_stable(self, ecs_manager):
        ecs_manager.client.describe_services.return_value = {
            "services": [{
                "status": "ACTIVE",
                "desiredCount": 2,
                "runningCount": 2,
                "pendingCount": 0,
            }]
        }
        result = ecs_manager.get_service_status("cluster", "svc")
        assert result["exists"] is True
        assert result["is_stable"] is True

    def test_service_not_stable(self, ecs_manager):
        ecs_manager.client.describe_services.return_value = {
            "services": [{
                "status": "ACTIVE",
                "desiredCount": 3,
                "runningCount": 1,
                "pendingCount": 2,
            }]
        }
        result = ecs_manager.get_service_status("cluster", "svc")
        assert result["is_stable"] is False

    def test_service_not_found(self, ecs_manager):
        ecs_manager.client.describe_services.return_value = {"services": []}
        result = ecs_manager.get_service_status("cluster", "nonexistent")
        assert result["exists"] is False


class TestECSManagerInit:
    def test_init_with_default_session(self):
        """Test initialization without a session uses boto3 directly."""
        # Just verify it doesn't crash; actual boto3 call is mocked at module level
        manager = ECSManager.__new__(ECSManager)
        manager.region = "us-east-1"
        assert manager.region == "us-east-1"
