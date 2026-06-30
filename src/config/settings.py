"""Application configuration settings."""

import os


class Settings:
    APP_NAME = "AWS ECS Workshop"
    APP_VERSION = "0.1.0"
    DEBUG = False

    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    ECS_CLUSTER_NAME = os.environ.get("ECS_CLUSTER_NAME", "ecs-workshop-cluster")
    ECR_REPO_NAME = os.environ.get("ECR_REPO_NAME", "ecs-workshop-app")

    CONTAINER_PORT = int(os.environ.get("CONTAINER_PORT", "5000"))
    CONTAINER_CPU = int(os.environ.get("CONTAINER_CPU", "256"))
    CONTAINER_MEMORY = int(os.environ.get("CONTAINER_MEMORY", "512"))

    LOG_GROUP_NAME = os.environ.get("LOG_GROUP_NAME", "/ecs/workshop")
    LOG_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "30"))

    HEALTH_CHECK_PATH = os.environ.get("HEALTH_CHECK_PATH", "/health")
    HEALTH_CHECK_INTERVAL = int(os.environ.get("HEALTH_CHECK_INTERVAL", "30"))
    HEALTH_CHECK_TIMEOUT = int(os.environ.get("HEALTH_CHECK_TIMEOUT", "5"))

    DESIRED_COUNT = int(os.environ.get("DESIRED_COUNT", "2"))
    MAX_CAPACITY = int(os.environ.get("MAX_CAPACITY", "10"))
    MIN_CAPACITY = int(os.environ.get("MIN_CAPACITY", "1"))

    @classmethod
    def get_ecs_config(cls):
        return {
            "cluster_name": cls.ECS_CLUSTER_NAME,
            "region": cls.AWS_REGION,
            "container_port": cls.CONTAINER_PORT,
            "cpu": cls.CONTAINER_CPU,
            "memory": cls.CONTAINER_MEMORY,
            "desired_count": cls.DESIRED_COUNT,
        }

    @classmethod
    def get_ecr_config(cls):
        return {
            "repo_name": cls.ECR_REPO_NAME,
            "region": cls.AWS_REGION,
        }

    @classmethod
    def get_log_config(cls):
        return {
            "log_group": cls.LOG_GROUP_NAME,
            "retention_days": cls.LOG_RETENTION_DAYS,
            "region": cls.AWS_REGION,
        }

    @classmethod
    def get_health_check_config(cls):
        return {
            "path": cls.HEALTH_CHECK_PATH,
            "interval": cls.HEALTH_CHECK_INTERVAL,
            "timeout": cls.HEALTH_CHECK_TIMEOUT,
        }

    @classmethod
    def validate(cls):
        errors = []
        if cls.CONTAINER_PORT < 1 or cls.CONTAINER_PORT > 65535:
            errors.append("CONTAINER_PORT must be between 1 and 65535")
        if cls.CONTAINER_CPU < 0:
            errors.append("CONTAINER_CPU must be non-negative")
        if cls.CONTAINER_MEMORY < 4:
            errors.append("CONTAINER_MEMORY must be at least 4")
        if cls.DESIRED_COUNT < 0:
            errors.append("DESIRED_COUNT must be non-negative")
        if cls.MIN_CAPACITY > cls.MAX_CAPACITY:
            errors.append("MIN_CAPACITY must be <= MAX_CAPACITY")
        if cls.LOG_RETENTION_DAYS < 1:
            errors.append("LOG_RETENTION_DAYS must be positive")
        return errors
