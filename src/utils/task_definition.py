"""ECS task definition builder utilities."""

import copy
import json

from src.utils.aws_base import AWSBaseManager, aws_api_call
from src.utils.converters import dict_to_env_vars, dict_to_tags


class TaskDefinitionBuilder:
    def __init__(self, family):
        self.family = family
        self.containers = []
        self.network_mode = "awsvpc"
        self.requires_compatibilities = ["FARGATE"]
        self.cpu = "256"
        self.memory = "512"
        self.execution_role_arn = ""
        self.task_role_arn = ""
        self.volumes = []
        self.tags = {}

    def add_container(
        self, name, image, cpu=256, memory=512, port=None,
        environment=None, essential=True, command=None, log_config=None,
    ):
        container = {
            "name": name,
            "image": image,
            "cpu": cpu,
            "memory": memory,
            "essential": essential,
        }
        if port is not None:
            container["portMappings"] = [
                {"containerPort": port, "protocol": "tcp"}
            ]
        if environment:
            container["environment"] = dict_to_env_vars(environment)
        if command:
            container["command"] = command if isinstance(command, list) else [command]
        if log_config:
            container["logConfiguration"] = log_config

        self.containers.append(container)
        return self

    def set_network_mode(self, mode):
        valid_modes = {"awsvpc", "bridge", "host", "none"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid network mode: {mode}. Must be one of: {valid_modes}")
        self.network_mode = mode
        return self

    def set_cpu_memory(self, cpu, memory):
        valid_cpu_memory = {
            "256": ["512", "1024", "2048"],
            "512": ["1024", "2048", "3072", "4096"],
            "1024": [str(i) for i in range(2048, 8193, 1024)],
            "2048": [str(i) for i in range(4096, 16385, 1024)],
            "4096": [str(i) for i in range(8192, 30721, 1024)],
        }
        cpu_str = str(cpu)
        memory_str = str(memory)

        if cpu_str not in valid_cpu_memory:
            raise ValueError(
                f"Invalid CPU value: {cpu}. Must be one of: {list(valid_cpu_memory.keys())}"
            )
        if memory_str not in valid_cpu_memory[cpu_str]:
            raise ValueError(
                f"Invalid memory value {memory} for CPU {cpu}. "
                f"Valid values: {valid_cpu_memory[cpu_str]}"
            )

        self.cpu = cpu_str
        self.memory = memory_str
        return self

    def set_execution_role(self, role_arn):
        self.execution_role_arn = role_arn
        return self

    def set_task_role(self, role_arn):
        self.task_role_arn = role_arn
        return self

    def add_volume(self, name, host_path=None):
        volume = {"name": name}
        if host_path:
            volume["host"] = {"sourcePath": host_path}
        self.volumes.append(volume)
        return self

    def add_tags(self, tags):
        self.tags.update(tags)
        return self

    def validate(self):
        errors = []
        if not self.family:
            errors.append("Task family name is required")
        if not self.containers:
            errors.append("At least one container definition is required")
        essential_count = sum(1 for c in self.containers if c.get("essential", True))
        if essential_count == 0:
            errors.append("At least one essential container is required")
        container_names = [c["name"] for c in self.containers]
        if len(container_names) != len(set(container_names)):
            errors.append("Container names must be unique")
        if self.requires_compatibilities == ["FARGATE"] and self.network_mode != "awsvpc":
            errors.append("Fargate tasks must use awsvpc network mode")
        return errors

    def build(self):
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid task definition: {'; '.join(errors)}")

        task_def = {
            "family": self.family,
            "containerDefinitions": copy.deepcopy(self.containers),
            "networkMode": self.network_mode,
            "requiresCompatibilities": self.requires_compatibilities,
            "cpu": self.cpu,
            "memory": self.memory,
        }
        if self.execution_role_arn:
            task_def["executionRoleArn"] = self.execution_role_arn
        if self.task_role_arn:
            task_def["taskRoleArn"] = self.task_role_arn
        if self.volumes:
            task_def["volumes"] = copy.deepcopy(self.volumes)
        if self.tags:
            task_def["tags"] = dict_to_tags(self.tags)
        return task_def

    def to_json(self, indent=2):
        return json.dumps(self.build(), indent=indent)


class TaskDefinitionManager(AWSBaseManager):
    _service_name = "ecs"

    @aws_api_call("register task definition")
    def register(self, task_definition):
        response = self.client.register_task_definition(**task_definition)
        return response["taskDefinition"]

    @aws_api_call("deregister task definition")
    def deregister(self, task_definition_arn):
        response = self.client.deregister_task_definition(
            taskDefinition=task_definition_arn
        )
        return response["taskDefinition"]

    @aws_api_call("describe task definition")
    def describe(self, task_definition):
        response = self.client.describe_task_definition(
            taskDefinition=task_definition
        )
        return response["taskDefinition"]

    @aws_api_call("list task definitions")
    def list_task_definitions(self, family_prefix=None, status="ACTIVE"):
        params = {"status": status}
        if family_prefix:
            params["familyPrefix"] = family_prefix
        response = self.client.list_task_definitions(**params)
        return response.get("taskDefinitionArns", [])

    def get_latest_revision(self, family):
        definitions = self.list_task_definitions(family_prefix=family)
        if not definitions:
            return None
        return definitions[-1]
