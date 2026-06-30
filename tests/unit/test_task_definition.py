"""Tests for task definition builder and manager."""

import json

import pytest
from botocore.exceptions import ClientError

from src.utils.task_definition import TaskDefinitionBuilder, TaskDefinitionManager


class TestTaskDefinitionBuilder:
    def test_basic_build(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest", port=80)
        result = builder.build()
        assert result["family"] == "my-task"
        assert len(result["containerDefinitions"]) == 1
        assert result["containerDefinitions"][0]["name"] == "web"

    def test_add_container_with_all_options(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container(
            "web", "nginx:latest", cpu=512, memory=1024, port=8080,
            environment={"ENV": "prod"}, essential=True,
            command=["nginx", "-g", "daemon off;"],
            log_config={"logDriver": "awslogs"},
        )
        result = builder.build()
        container = result["containerDefinitions"][0]
        assert container["cpu"] == 512
        assert container["memory"] == 1024
        assert container["portMappings"] == [{"containerPort": 8080, "protocol": "tcp"}]
        assert container["environment"] == [{"name": "ENV", "value": "prod"}]
        assert container["command"] == ["nginx", "-g", "daemon off;"]
        assert container["logConfiguration"] == {"logDriver": "awslogs"}

    def test_add_container_string_command(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest", command="echo hello")
        result = builder.build()
        assert result["containerDefinitions"][0]["command"] == ["echo hello"]

    def test_add_container_no_port(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("worker", "worker:latest")
        result = builder.build()
        assert "portMappings" not in result["containerDefinitions"][0]

    def test_method_chaining(self):
        builder = TaskDefinitionBuilder("my-task")
        result = (
            builder
            .add_container("web", "nginx:latest", port=80)
            .set_cpu_memory(512, 1024)
            .set_execution_role("arn:aws:iam::123:role/exec")
            .set_task_role("arn:aws:iam::123:role/task")
            .add_volume("data")
            .add_tags({"env": "prod"})
            .build()
        )
        assert result["cpu"] == "512"
        assert result["memory"] == "1024"
        assert result["executionRoleArn"] == "arn:aws:iam::123:role/exec"
        assert result["taskRoleArn"] == "arn:aws:iam::123:role/task"
        assert result["volumes"] == [{"name": "data"}]
        assert result["tags"] == [{"key": "env", "value": "prod"}]

    def test_add_volume_with_host_path(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest")
        builder.add_volume("data", host_path="/mnt/data")
        result = builder.build()
        assert result["volumes"] == [
            {"name": "data", "host": {"sourcePath": "/mnt/data"}}
        ]

    def test_set_network_mode(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest")
        builder.requires_compatibilities = ["EC2"]
        builder.set_network_mode("bridge")
        result = builder.build()
        assert result["networkMode"] == "bridge"

    def test_set_network_mode_invalid(self):
        builder = TaskDefinitionBuilder("my-task")
        with pytest.raises(ValueError, match="Invalid network mode"):
            builder.set_network_mode("invalid")

    def test_set_cpu_memory_valid(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.set_cpu_memory(256, 512)
        assert builder.cpu == "256"
        assert builder.memory == "512"

    def test_set_cpu_memory_invalid_cpu(self):
        builder = TaskDefinitionBuilder("my-task")
        with pytest.raises(ValueError, match="Invalid CPU value"):
            builder.set_cpu_memory(128, 512)

    def test_set_cpu_memory_invalid_memory(self):
        builder = TaskDefinitionBuilder("my-task")
        with pytest.raises(ValueError, match="Invalid memory value"):
            builder.set_cpu_memory(256, 256)

    def test_validate_no_family(self):
        builder = TaskDefinitionBuilder("")
        errors = builder.validate()
        assert "Task family name is required" in errors

    def test_validate_no_containers(self):
        builder = TaskDefinitionBuilder("my-task")
        errors = builder.validate()
        assert "At least one container definition is required" in errors

    def test_validate_no_essential_container(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.containers.append({"name": "sidecar", "essential": False})
        errors = builder.validate()
        assert "At least one essential container is required" in errors

    def test_validate_duplicate_container_names(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest")
        builder.add_container("web", "nginx:latest")
        errors = builder.validate()
        assert "Container names must be unique" in errors

    def test_validate_fargate_requires_awsvpc(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest")
        builder.network_mode = "bridge"
        errors = builder.validate()
        assert "Fargate tasks must use awsvpc network mode" in errors

    def test_build_fails_on_validation_errors(self):
        builder = TaskDefinitionBuilder("")
        with pytest.raises(ValueError, match="Invalid task definition"):
            builder.build()

    def test_to_json(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest", port=80)
        json_str = builder.to_json()
        parsed = json.loads(json_str)
        assert parsed["family"] == "my-task"

    def test_build_without_optional_fields(self):
        builder = TaskDefinitionBuilder("my-task")
        builder.add_container("web", "nginx:latest")
        result = builder.build()
        assert "executionRoleArn" not in result
        assert "taskRoleArn" not in result
        assert "volumes" not in result
        assert "tags" not in result


@pytest.fixture
def td_manager(mock_session):
    return TaskDefinitionManager(region="us-east-1", session=mock_session)


class TestTaskDefinitionManager:
    def test_register(self, td_manager):
        td_manager.client.register_task_definition.return_value = {
            "taskDefinition": {"family": "my-task", "revision": 1}
        }
        result = td_manager.register({"family": "my-task"})
        assert result["family"] == "my-task"

    def test_register_error(self, td_manager):
        td_manager.client.register_task_definition.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterException", "Message": "bad"}},
            "RegisterTaskDefinition",
        )
        with pytest.raises(RuntimeError, match="Failed to register"):
            td_manager.register({"family": "bad"})

    def test_deregister(self, td_manager):
        td_manager.client.deregister_task_definition.return_value = {
            "taskDefinition": {"status": "INACTIVE"}
        }
        result = td_manager.deregister("arn:task:1")
        assert result["status"] == "INACTIVE"

    def test_deregister_error(self, td_manager):
        td_manager.client.deregister_task_definition.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterException", "Message": "bad"}},
            "DeregisterTaskDefinition",
        )
        with pytest.raises(RuntimeError, match="Failed to deregister"):
            td_manager.deregister("bad-arn")

    def test_describe(self, td_manager):
        td_manager.client.describe_task_definition.return_value = {
            "taskDefinition": {"family": "my-task", "revision": 1}
        }
        result = td_manager.describe("my-task:1")
        assert result["family"] == "my-task"

    def test_describe_error(self, td_manager):
        td_manager.client.describe_task_definition.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterException", "Message": "bad"}},
            "DescribeTaskDefinition",
        )
        with pytest.raises(RuntimeError, match="Failed to describe"):
            td_manager.describe("nonexistent")

    def test_list_task_definitions(self, td_manager):
        td_manager.client.list_task_definitions.return_value = {
            "taskDefinitionArns": ["arn:task:1", "arn:task:2"]
        }
        result = td_manager.list_task_definitions()
        assert len(result) == 2

    def test_list_task_definitions_with_prefix(self, td_manager):
        td_manager.client.list_task_definitions.return_value = {
            "taskDefinitionArns": []
        }
        td_manager.list_task_definitions(family_prefix="my-task")
        call_kwargs = td_manager.client.list_task_definitions.call_args[1]
        assert call_kwargs["familyPrefix"] == "my-task"

    def test_list_task_definitions_error(self, td_manager):
        td_manager.client.list_task_definitions.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "ListTaskDefinitions",
        )
        with pytest.raises(RuntimeError, match="Failed to list task definitions"):
            td_manager.list_task_definitions()

    def test_get_latest_revision(self, td_manager):
        td_manager.client.list_task_definitions.return_value = {
            "taskDefinitionArns": ["arn:task:1", "arn:task:2", "arn:task:3"]
        }
        result = td_manager.get_latest_revision("my-task")
        assert result == "arn:task:3"

    def test_get_latest_revision_empty(self, td_manager):
        td_manager.client.list_task_definitions.return_value = {
            "taskDefinitionArns": []
        }
        result = td_manager.get_latest_revision("nonexistent")
        assert result is None
