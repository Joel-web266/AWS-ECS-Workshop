"""Tests for data models."""

from datetime import datetime, timezone

from src.app.models import (
    ContainerDefinition,
    DeploymentRecord,
    ServiceConfig,
    ServiceStatus,
    TaskDefinitionConfig,
    TaskStatus,
)


class TestTaskStatus:
    def test_status_values(self):
        assert TaskStatus.PENDING.value == "PENDING"
        assert TaskStatus.RUNNING.value == "RUNNING"
        assert TaskStatus.STOPPED.value == "STOPPED"
        assert TaskStatus.FAILED.value == "FAILED"


class TestServiceStatus:
    def test_status_values(self):
        assert ServiceStatus.ACTIVE.value == "ACTIVE"
        assert ServiceStatus.DRAINING.value == "DRAINING"
        assert ServiceStatus.INACTIVE.value == "INACTIVE"


class TestContainerDefinition:
    def test_default_values(self):
        container = ContainerDefinition(name="web", image="nginx:latest")
        assert container.cpu == 256
        assert container.memory == 512
        assert container.port == 80
        assert container.environment == {}
        assert container.essential is True

    def test_validate_valid_container(self):
        container = ContainerDefinition(name="web", image="nginx:latest")
        assert container.validate() == []

    def test_validate_empty_name(self):
        container = ContainerDefinition(name="", image="nginx:latest")
        errors = container.validate()
        assert "Container name is required" in errors

    def test_validate_whitespace_name(self):
        container = ContainerDefinition(name="  ", image="nginx:latest")
        errors = container.validate()
        assert "Container name is required" in errors

    def test_validate_empty_image(self):
        container = ContainerDefinition(name="web", image="")
        errors = container.validate()
        assert "Container image is required" in errors

    def test_validate_negative_cpu(self):
        container = ContainerDefinition(name="web", image="nginx", cpu=-1)
        errors = container.validate()
        assert "CPU must be non-negative" in errors

    def test_validate_low_memory(self):
        container = ContainerDefinition(name="web", image="nginx", memory=2)
        errors = container.validate()
        assert "Memory must be at least 4 MiB" in errors

    def test_validate_invalid_port(self):
        container = ContainerDefinition(name="web", image="nginx", port=70000)
        errors = container.validate()
        assert "Port must be between 0 and 65535" in errors

    def test_validate_negative_port(self):
        container = ContainerDefinition(name="web", image="nginx", port=-1)
        errors = container.validate()
        assert "Port must be between 0 and 65535" in errors

    def test_to_dict(self):
        container = ContainerDefinition(
            name="web", image="nginx:latest", cpu=512, memory=1024,
            port=8080, environment={"ENV": "prod"}, essential=True,
        )
        d = container.to_dict()
        assert d["name"] == "web"
        assert d["image"] == "nginx:latest"
        assert d["cpu"] == 512
        assert d["memory"] == 1024
        assert d["portMappings"] == [{"containerPort": 8080, "protocol": "tcp"}]
        assert d["environment"] == [{"name": "ENV", "value": "prod"}]
        assert d["essential"] is True

    def test_to_dict_empty_env(self):
        container = ContainerDefinition(name="web", image="nginx:latest")
        d = container.to_dict()
        assert d["environment"] == []


class TestTaskDefinitionConfig:
    def test_default_values(self):
        config = TaskDefinitionConfig(family="my-task")
        assert config.network_mode == "awsvpc"
        assert config.requires_compatibilities == ["FARGATE"]

    def test_validate_valid(self):
        config = TaskDefinitionConfig(
            family="my-task",
            containers=[ContainerDefinition(name="web", image="nginx")],
        )
        assert config.validate() == []

    def test_validate_empty_family(self):
        config = TaskDefinitionConfig(family="")
        errors = config.validate()
        assert "Task family name is required" in errors

    def test_validate_no_containers(self):
        config = TaskDefinitionConfig(family="my-task")
        errors = config.validate()
        assert "At least one container definition is required" in errors

    def test_validate_invalid_network_mode(self):
        config = TaskDefinitionConfig(
            family="my-task",
            containers=[ContainerDefinition(name="web", image="nginx")],
            network_mode="invalid",
        )
        errors = config.validate()
        assert any("Invalid network mode" in e for e in errors)

    def test_validate_propagates_container_errors(self):
        config = TaskDefinitionConfig(
            family="my-task",
            containers=[ContainerDefinition(name="", image="")],
        )
        errors = config.validate()
        assert "Container name is required" in errors
        assert "Container image is required" in errors

    def test_to_dict(self):
        config = TaskDefinitionConfig(
            family="my-task",
            containers=[ContainerDefinition(name="web", image="nginx")],
            execution_role_arn="arn:role/exec",
            task_role_arn="arn:role/task",
        )
        d = config.to_dict()
        assert d["family"] == "my-task"
        assert len(d["containerDefinitions"]) == 1
        assert d["executionRoleArn"] == "arn:role/exec"
        assert d["taskRoleArn"] == "arn:role/task"

    def test_to_dict_without_optional_roles(self):
        config = TaskDefinitionConfig(
            family="my-task",
            containers=[ContainerDefinition(name="web", image="nginx")],
        )
        d = config.to_dict()
        assert "executionRoleArn" not in d
        assert "taskRoleArn" not in d


class TestServiceConfig:
    def test_default_values(self):
        config = ServiceConfig(
            name="svc", cluster="cluster", task_definition="task:1"
        )
        assert config.desired_count == 1
        assert config.launch_type == "FARGATE"
        assert config.assign_public_ip is True

    def test_validate_valid(self):
        config = ServiceConfig(
            name="svc", cluster="cluster", task_definition="task:1"
        )
        assert config.validate() == []

    def test_validate_empty_name(self):
        config = ServiceConfig(name="", cluster="c", task_definition="t")
        errors = config.validate()
        assert "Service name is required" in errors

    def test_validate_empty_cluster(self):
        config = ServiceConfig(name="s", cluster="", task_definition="t")
        errors = config.validate()
        assert "Cluster name is required" in errors

    def test_validate_empty_task_definition(self):
        config = ServiceConfig(name="s", cluster="c", task_definition="")
        errors = config.validate()
        assert "Task definition is required" in errors

    def test_validate_negative_desired_count(self):
        config = ServiceConfig(
            name="s", cluster="c", task_definition="t", desired_count=-1
        )
        errors = config.validate()
        assert "Desired count must be non-negative" in errors

    def test_validate_invalid_launch_type(self):
        config = ServiceConfig(
            name="s", cluster="c", task_definition="t", launch_type="INVALID"
        )
        errors = config.validate()
        assert any("Invalid launch type" in e for e in errors)

    def test_validate_negative_grace_period(self):
        config = ServiceConfig(
            name="s", cluster="c", task_definition="t",
            health_check_grace_period=-1,
        )
        errors = config.validate()
        assert "Health check grace period must be non-negative" in errors

    def test_get_network_configuration(self):
        config = ServiceConfig(
            name="svc", cluster="c", task_definition="t",
            subnets=["subnet-1", "subnet-2"],
            security_groups=["sg-1"],
            assign_public_ip=True,
        )
        net_config = config.get_network_configuration()
        assert net_config["awsvpcConfiguration"]["subnets"] == ["subnet-1", "subnet-2"]
        assert net_config["awsvpcConfiguration"]["securityGroups"] == ["sg-1"]
        assert net_config["awsvpcConfiguration"]["assignPublicIp"] == "ENABLED"

    def test_get_network_configuration_disabled_ip(self):
        config = ServiceConfig(
            name="svc", cluster="c", task_definition="t",
            assign_public_ip=False,
        )
        net_config = config.get_network_configuration()
        assert net_config["awsvpcConfiguration"]["assignPublicIp"] == "DISABLED"


class TestDeploymentRecord:
    def test_default_values(self):
        record = DeploymentRecord(
            service_name="svc", task_definition="task:1", desired_count=2
        )
        assert record.status == "IN_PROGRESS"
        assert record.errors == []

    def test_mark_complete(self):
        record = DeploymentRecord(
            service_name="svc", task_definition="task:1", desired_count=2
        )
        record.mark_complete()
        assert record.status == "COMPLETE"

    def test_mark_failed(self):
        record = DeploymentRecord(
            service_name="svc", task_definition="task:1", desired_count=2
        )
        record.mark_failed("Timeout waiting for stabilization")
        assert record.status == "FAILED"
        assert "Timeout waiting for stabilization" in record.errors

    def test_is_successful_true(self):
        record = DeploymentRecord(
            service_name="svc", task_definition="task:1", desired_count=2
        )
        record.mark_complete()
        assert record.is_successful() is True

    def test_is_successful_false_status(self):
        record = DeploymentRecord(
            service_name="svc", task_definition="task:1", desired_count=2
        )
        assert record.is_successful() is False

    def test_is_successful_false_errors(self):
        record = DeploymentRecord(
            service_name="svc", task_definition="task:1", desired_count=2
        )
        record.status = "COMPLETE"
        record.errors.append("warning")
        assert record.is_successful() is False

    def test_to_dict(self):
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        record = DeploymentRecord(
            service_name="svc", task_definition="task:1",
            desired_count=2, deployment_id="deploy-123", timestamp=ts,
        )
        d = record.to_dict()
        assert d["service_name"] == "svc"
        assert d["task_definition"] == "task:1"
        assert d["desired_count"] == 2
        assert d["status"] == "IN_PROGRESS"
        assert d["deployment_id"] == "deploy-123"
        assert d["timestamp"] == "2024-01-01T12:00:00+00:00"
        assert d["errors"] == []
