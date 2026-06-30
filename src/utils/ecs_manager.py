"""ECS cluster and service management utilities."""

from src.utils.aws_base import AWSBaseManager, aws_api_call
from src.utils.converters import dict_to_tags


class ECSManager(AWSBaseManager):
    _service_name = "ecs"

    @aws_api_call("create cluster '{cluster_name}'")
    def create_cluster(self, cluster_name, tags=None):
        params = {"clusterName": cluster_name}
        if tags:
            params["tags"] = dict_to_tags(tags)
        response = self.client.create_cluster(**params)
        return response["cluster"]

    @aws_api_call("delete cluster '{cluster_name}'")
    def delete_cluster(self, cluster_name):
        response = self.client.delete_cluster(cluster=cluster_name)
        return response["cluster"]

    @aws_api_call("list clusters")
    def list_clusters(self):
        response = self.client.list_clusters()
        return response.get("clusterArns", [])

    @aws_api_call("describe cluster '{cluster_name}'")
    def describe_cluster(self, cluster_name):
        response = self.client.describe_clusters(clusters=[cluster_name])
        clusters = response.get("clusters", [])
        if not clusters:
            return None
        return clusters[0]

    @aws_api_call("create service '{service_config.name}'")
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

        response = self.client.create_service(**params)
        return response["service"]

    @aws_api_call("update service '{service_name}'")
    def update_service(self, cluster, service_name, desired_count=None, task_definition=None):
        params = {"cluster": cluster, "service": service_name}
        if desired_count is not None:
            params["desiredCount"] = desired_count
        if task_definition is not None:
            params["taskDefinition"] = task_definition

        response = self.client.update_service(**params)
        return response["service"]

    @aws_api_call("delete service '{service_name}'")
    def delete_service(self, cluster, service_name, force=False):
        response = self.client.delete_service(
            cluster=cluster, service=service_name, force=force
        )
        return response["service"]

    @aws_api_call("list services in cluster '{cluster}'")
    def list_services(self, cluster):
        response = self.client.list_services(cluster=cluster)
        return response.get("serviceArns", [])

    @aws_api_call("describe service '{service_name}'")
    def describe_service(self, cluster, service_name):
        response = self.client.describe_services(
            cluster=cluster, services=[service_name]
        )
        services = response.get("services", [])
        if not services:
            return None
        return services[0]

    @aws_api_call("list tasks")
    def list_tasks(self, cluster, service_name=None):
        params = {"cluster": cluster}
        if service_name:
            params["serviceName"] = service_name

        response = self.client.list_tasks(**params)
        return response.get("taskArns", [])

    @aws_api_call("stop task '{task_arn}'")
    def stop_task(self, cluster, task_arn, reason="Stopped by user"):
        response = self.client.stop_task(
            cluster=cluster, task=task_arn, reason=reason
        )
        return response["task"]

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
