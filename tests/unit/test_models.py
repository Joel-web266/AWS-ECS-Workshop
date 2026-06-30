"""Tests for data models - partial coverage only."""

from src.app.models import ContainerDefinition, TaskStatus


class TestContainerDefinition:
    def test_default_values(self):
        container = ContainerDefinition(name="web", image="nginx:latest")
        assert container.cpu == 256
        assert container.memory == 512
        assert container.port == 80

    def test_validate_valid_container(self):
        container = ContainerDefinition(name="web", image="nginx:latest")
        errors = container.validate()
        assert len(errors) == 0


class TestTaskStatus:
    def test_status_values(self):
        assert TaskStatus.RUNNING.value == "RUNNING"
        assert TaskStatus.STOPPED.value == "STOPPED"
