"""ECR repository management utilities."""

import base64
import re

from botocore.exceptions import ClientError

from src.utils.aws_base import AWSBaseManager, aws_api_call


class ECRManager(AWSBaseManager):
    _service_name = "ecr"

    def create_repository(self, repo_name, image_tag_mutability="MUTABLE", scan_on_push=False):
        if not self._is_valid_repo_name(repo_name):
            raise ValueError(
                f"Invalid repository name: '{repo_name}'. "
                "Must match pattern: [a-z0-9._/-]+"
            )
        try:
            response = self.client.create_repository(
                repositoryName=repo_name,
                imageTagMutability=image_tag_mutability,
                imageScanningConfiguration={"scanOnPush": scan_on_push},
            )
            return response["repository"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "RepositoryAlreadyExistsException":
                return self.describe_repository(repo_name)
            raise RuntimeError(f"Failed to create repository '{repo_name}': {e}") from e

    @aws_api_call("delete repository '{repo_name}'")
    def delete_repository(self, repo_name, force=False):
        response = self.client.delete_repository(
            repositoryName=repo_name, force=force
        )
        return response["repository"]

    def describe_repository(self, repo_name):
        try:
            response = self.client.describe_repositories(repositoryNames=[repo_name])
            repos = response.get("repositories", [])
            if not repos:
                return None
            return repos[0]
        except ClientError as e:
            if e.response["Error"]["Code"] == "RepositoryNotFoundException":
                return None
            raise RuntimeError(f"Failed to describe repository '{repo_name}': {e}") from e

    @aws_api_call("list repositories")
    def list_repositories(self):
        response = self.client.describe_repositories()
        return response.get("repositories", [])

    @aws_api_call("list images in '{repo_name}'")
    def list_images(self, repo_name):
        response = self.client.list_images(repositoryName=repo_name)
        return response.get("imageIds", [])

    @aws_api_call("get login token")
    def get_login_token(self):
        response = self.client.get_authorization_token()
        auth_data = response["authorizationData"][0]
        token = base64.b64decode(auth_data["authorizationToken"]).decode("utf-8")
        username, password = token.split(":")
        endpoint = auth_data["proxyEndpoint"]
        return {"username": username, "password": password, "endpoint": endpoint}

    @aws_api_call("set lifecycle policy for '{repo_name}'")
    def set_lifecycle_policy(self, repo_name, max_image_count=100):
        policy = (
            '{"rules":[{"rulePriority":1,"description":"Keep last '
            + str(max_image_count)
            + ' images","selection":{"tagStatus":"any","countType":"imageCountMoreThan",'
            + '"countNumber":'
            + str(max_image_count)
            + '},"action":{"type":"expire"}}]}'
        )
        self.client.put_lifecycle_policy(
            repositoryName=repo_name, lifecyclePolicyText=policy
        )
        return True

    def get_image_uri(self, repo_name, tag="latest"):
        repo = self.describe_repository(repo_name)
        if not repo:
            raise ValueError(f"Repository '{repo_name}' not found")
        return f"{repo['repositoryUri']}:{tag}"

    @aws_api_call("batch delete images")
    def batch_delete_images(self, repo_name, image_ids):
        if not image_ids:
            return {"successes": [], "failures": []}
        response = self.client.batch_delete_image(
            repositoryName=repo_name, imageIds=image_ids
        )
        return {
            "successes": response.get("imageIds", []),
            "failures": response.get("failures", []),
        }

    @staticmethod
    def _is_valid_repo_name(name):
        if not name:
            return False
        pattern = r"^[a-z0-9][a-z0-9._/-]*$"
        return bool(re.match(pattern, name))

    def get_repository_policy(self, repo_name):
        try:
            response = self.client.get_repository_policy(repositoryName=repo_name)
            return response.get("policyText", "")
        except ClientError as e:
            if e.response["Error"]["Code"] == "RepositoryPolicyNotFoundException":
                return None
            raise RuntimeError(
                f"Failed to get repository policy for '{repo_name}': {e}"
            ) from e
