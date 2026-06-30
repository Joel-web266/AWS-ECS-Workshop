"""ECS cluster and service management utilities."""

import boto3
from botocore.exceptions import ClientError


class ECSManager:
    def __init__(self, region="us-east-1", session=None):
        if session:
            self.client = session.client("ecs", region_name=region)
        else:
            self.client = boto3.client("ecs", region_name=region)
        self.region = region

    def create_cluster(self, cluster_name, tags=None):
        params = {"clusterName": cluster_name}
        if tags:
            params["tags"] = [{"key": k, "value": v} for k, v in tags.items()]
        try:
            response = self.client.create_cluster(**params)
            return response["cluster"]
        except ClientError as e:
            raise RuntimeError(f"Failed to create cluster '{cluster_name}': {e}") from e

    def delete_cluster(self, cluster_name):
        try:
            response = self.client.delete_cluster(cluster=cluster_name)
            return response["cluster"]
        except ClientError as e:
            raise RuntimeError(f"Failed to delete cluster '{cluster_name}': {e}") from e

    def list_clusters(self):
        try:
            response = self.client.list_clusters()
            return response.get("clusterArns", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list clusters: {e}") from e

    def describe_cluster(self, cluster_name):
        try:
            response = self.client.describe_clusters(clusters=[cluster_name])
            clusters = response.get("clusters", [])
            if not clusters:
                return None
            return clusters[0]
        except ClientError as e:
            raise RuntimeError(f"Failed to describe cluster '{cluster_name}': {e}") from e

    def create_service(self, service_config):
        errors = service_config.validate()
        if errors:
            raise ValueError(f"Invalid service config: {', '.join(errors)}")

        params = {
            "cluster": service_config.cluster,
            "serviceName": service_config.name,
            "taskDefinition": service_config.task_definition,
            "desiredCount": service_config.desired_count,
            "launchType": service_config.launch_type,
        }

        if service_config.launch_type == "FARGATE":
            params["networkConfiguration"] = service_config.get_network_configuration()

        if service_config.health_check_grace_period > 0:
            params["healthCheckGracePeriodSeconds"] = service_config.health_check_grace_period

        try:
            response = self.client.create_service(**params)
            return response["service"]
        except ClientError as e:
            raise RuntimeError(
                f"Failed to create service '{service_config.name}': {e}"
            ) from e

    def update_service(self, cluster, service_name, desired_count=None, task_definition=None):
        params = {"cluster": cluster, "service": service_name}
        if desired_count is not None:
            params["desiredCount"] = desired_count
        if task_definition is not None:
            params["taskDefinition"] = task_definition

        try:
            response = self.client.update_service(**params)
            return response["service"]
        except ClientError as e:
            raise RuntimeError(f"Failed to update service '{service_name}': {e}") from e

    def delete_service(self, cluster, service_name, force=False):
        try:
            response = self.client.delete_service(
                cluster=cluster, service=service_name, force=force
            )
            return response["service"]
        except ClientError as e:
            raise RuntimeError(f"Failed to delete service '{service_name}': {e}") from e

    def list_services(self, cluster):
        try:
            response = self.client.list_services(cluster=cluster)
            return response.get("serviceArns", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list services in cluster '{cluster}': {e}") from e

    def describe_service(self, cluster, service_name):
        try:
            response = self.client.describe_services(
                cluster=cluster, services=[service_name]
            )
            services = response.get("services", [])
            if not services:
                return None
            return services[0]
        except ClientError as e:
            raise RuntimeError(
                f"Failed to describe service '{service_name}': {e}"
            ) from e

    def list_tasks(self, cluster, service_name=None):
        params = {"cluster": cluster}
        if service_name:
            params["serviceName"] = service_name

        try:
            response = self.client.list_tasks(**params)
            return response.get("taskArns", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list tasks: {e}") from e

    def stop_task(self, cluster, task_arn, reason="Stopped by user"):
        try:
            response = self.client.stop_task(
                cluster=cluster, task=task_arn, reason=reason
            )
            return response["task"]
        except ClientError as e:
            raise RuntimeError(f"Failed to stop task '{task_arn}': {e}") from e

    def get_service_status(self, cluster, service_name):
        service = self.describe_service(cluster, service_name)
        if not service:
            return {"exists": False}
        return {
            "exists": True,
            "status": service.get("status"),
            "desired_count": service.get("desiredCount", 0),
            "running_count": service.get("runningCount", 0),
            "pending_count": service.get("pendingCount", 0),
            "is_stable": service.get("runningCount", 0) == service.get("desiredCount", 0),
        }
