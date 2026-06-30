"""Data models for the ECS Workshop application."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.utils.converters import dict_to_env_vars


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class ServiceStatus(Enum):
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    INACTIVE = "INACTIVE"


@dataclass
class ContainerDefinition:
    name: str
    image: str
    cpu: int = 256
    memory: int = 512
    port: int = 80
    environment: dict = field(default_factory=dict)
    essential: bool = True

    def validate(self) -> list[str]:
        errors = []
        if not self.name or not self.name.strip():
            errors.append("Container name is required")
        if not self.image or not self.image.strip():
            errors.append("Container image is required")
        if self.cpu < 0:
            errors.append("CPU must be non-negative")
        if self.memory < 4:
            errors.append("Memory must be at least 4 MiB")
        if self.port < 0 or self.port > 65535:
            errors.append("Port must be between 0 and 65535")
        return errors

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "image": self.image,
            "cpu": self.cpu,
            "memory": self.memory,
            "portMappings": [{"containerPort": self.port, "protocol": "tcp"}],
            "environment": dict_to_env_vars(self.environment),
            "essential": self.essential,
        }


@dataclass
class TaskDefinitionConfig:
    family: str
    containers: list[ContainerDefinition] = field(default_factory=list)
    network_mode: str = "awsvpc"
    requires_compatibilities: list[str] = field(default_factory=lambda: ["FARGATE"])
    execution_role_arn: str = ""
    task_role_arn: str = ""
    cpu: str = "256"
    memory: str = "512"

    def validate(self) -> list[str]:
        errors = []
        if not self.family or not self.family.strip():
            errors.append("Task family name is required")
        if not self.containers:
            errors.append("At least one container definition is required")
        valid_network_modes = {"awsvpc", "bridge", "host", "none"}
        if self.network_mode not in valid_network_modes:
            errors.append(f"Invalid network mode: {self.network_mode}")
        for container in self.containers:
            errors.extend(container.validate())
        return errors

    def to_dict(self) -> dict:
        result = {
            "family": self.family,
            "containerDefinitions": [c.to_dict() for c in self.containers],
            "networkMode": self.network_mode,
            "requiresCompatibilities": self.requires_compatibilities,
            "cpu": self.cpu,
            "memory": self.memory,
        }
        if self.execution_role_arn:
            result["executionRoleArn"] = self.execution_role_arn
        if self.task_role_arn:
            result["taskRoleArn"] = self.task_role_arn
        return result


@dataclass
class ServiceConfig:
    name: str
    cluster: str
    task_definition: str
    desired_count: int = 1
    launch_type: str = "FARGATE"
    subnets: list[str] = field(default_factory=list)
    security_groups: list[str] = field(default_factory=list)
    assign_public_ip: bool = True
    health_check_grace_period: int = 60

    def validate(self) -> list[str]:
        errors = []
        if not self.name or not self.name.strip():
            errors.append("Service name is required")
        if not self.cluster or not self.cluster.strip():
            errors.append("Cluster name is required")
        if not self.task_definition or not self.task_definition.strip():
            errors.append("Task definition is required")
        if self.desired_count < 0:
            errors.append("Desired count must be non-negative")
        if self.launch_type not in {"FARGATE", "EC2", "EXTERNAL"}:
            errors.append(f"Invalid launch type: {self.launch_type}")
        if self.health_check_grace_period < 0:
            errors.append("Health check grace period must be non-negative")
        return errors

    def get_network_configuration(self) -> dict:
        return {
            "awsvpcConfiguration": {
                "subnets": self.subnets,
                "securityGroups": self.security_groups,
                "assignPublicIp": "ENABLED" if self.assign_public_ip else "DISABLED",
            }
        }


@dataclass
class DeploymentRecord:
    service_name: str
    task_definition: str
    desired_count: int
    status: str = "IN_PROGRESS"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deployment_id: str = ""
    errors: list[str] = field(default_factory=list)

    def mark_complete(self) -> None:
        self.status = "COMPLETE"

    def mark_failed(self, error: str) -> None:
        self.status = "FAILED"
        self.errors.append(error)

    def is_successful(self) -> bool:
        return self.status == "COMPLETE" and len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "task_definition": self.task_definition,
            "desired_count": self.desired_count,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "deployment_id": self.deployment_id,
            "errors": self.errors,
        }
