"""Tests for application settings."""


from src.config.settings import Settings


class TestSettingsDefaults:
    def test_app_name(self):
        assert Settings.APP_NAME == "AWS ECS Workshop"

    def test_app_version(self):
        assert Settings.APP_VERSION == "0.1.0"

    def test_default_region(self):
        assert Settings.AWS_REGION == "us-east-1"

    def test_default_cluster_name(self):
        assert Settings.ECS_CLUSTER_NAME == "ecs-workshop-cluster"

    def test_default_container_port(self):
        assert Settings.CONTAINER_PORT == 5000

    def test_default_log_group(self):
        assert Settings.LOG_GROUP_NAME == "/ecs/workshop"


class TestGetConfigs:
    def test_get_ecs_config(self):
        config = Settings.get_ecs_config()
        assert "cluster_name" in config
        assert "region" in config
        assert "container_port" in config
        assert "cpu" in config
        assert "memory" in config
        assert "desired_count" in config

    def test_get_ecr_config(self):
        config = Settings.get_ecr_config()
        assert "repo_name" in config
        assert "region" in config

    def test_get_log_config(self):
        config = Settings.get_log_config()
        assert "log_group" in config
        assert "retention_days" in config
        assert "region" in config

    def test_get_health_check_config(self):
        config = Settings.get_health_check_config()
        assert "path" in config
        assert "interval" in config
        assert "timeout" in config


class TestValidation:
    def test_validate_defaults_pass(self):
        errors = Settings.validate()
        assert errors == []

    def test_validate_invalid_port(self):
        original = Settings.CONTAINER_PORT
        try:
            Settings.CONTAINER_PORT = 0
            errors = Settings.validate()
            assert "CONTAINER_PORT must be between 1 and 65535" in errors
        finally:
            Settings.CONTAINER_PORT = original

    def test_validate_negative_cpu(self):
        original = Settings.CONTAINER_CPU
        try:
            Settings.CONTAINER_CPU = -1
            errors = Settings.validate()
            assert "CONTAINER_CPU must be non-negative" in errors
        finally:
            Settings.CONTAINER_CPU = original

    def test_validate_low_memory(self):
        original = Settings.CONTAINER_MEMORY
        try:
            Settings.CONTAINER_MEMORY = 2
            errors = Settings.validate()
            assert "CONTAINER_MEMORY must be at least 4" in errors
        finally:
            Settings.CONTAINER_MEMORY = original

    def test_validate_negative_desired_count(self):
        original = Settings.DESIRED_COUNT
        try:
            Settings.DESIRED_COUNT = -1
            errors = Settings.validate()
            assert "DESIRED_COUNT must be non-negative" in errors
        finally:
            Settings.DESIRED_COUNT = original

    def test_validate_min_greater_than_max(self):
        orig_min = Settings.MIN_CAPACITY
        orig_max = Settings.MAX_CAPACITY
        try:
            Settings.MIN_CAPACITY = 20
            Settings.MAX_CAPACITY = 5
            errors = Settings.validate()
            assert "MIN_CAPACITY must be <= MAX_CAPACITY" in errors
        finally:
            Settings.MIN_CAPACITY = orig_min
            Settings.MAX_CAPACITY = orig_max

    def test_validate_negative_retention(self):
        original = Settings.LOG_RETENTION_DAYS
        try:
            Settings.LOG_RETENTION_DAYS = 0
            errors = Settings.validate()
            assert "LOG_RETENTION_DAYS must be positive" in errors
        finally:
            Settings.LOG_RETENTION_DAYS = original
