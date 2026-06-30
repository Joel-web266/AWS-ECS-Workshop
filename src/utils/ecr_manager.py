"""ECR repository management utilities."""

import base64
import binascii
import json
import re

import boto3
from botocore.exceptions import ClientError


class ECRManager:
    def __init__(self, region="us-east-1", session=None):
        if session:
            self.client = session.client("ecr", region_name=region)
        else:
            self.client = boto3.client("ecr", region_name=region)
        self.region = region

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

    def delete_repository(self, repo_name, force=False):
        try:
            response = self.client.delete_repository(
                repositoryName=repo_name, force=force
            )
            return response["repository"]
        except ClientError as e:
            raise RuntimeError(f"Failed to delete repository '{repo_name}': {e}") from e

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

    def list_repositories(self):
        try:
            response = self.client.describe_repositories()
            return response.get("repositories", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list repositories: {e}") from e

    def list_images(self, repo_name):
        try:
            response = self.client.list_images(repositoryName=repo_name)
            return response.get("imageIds", [])
        except ClientError as e:
            raise RuntimeError(f"Failed to list images in '{repo_name}': {e}") from e

    def get_login_token(self):
        try:
            response = self.client.get_authorization_token()
            auth_data = response["authorizationData"][0]
            token = base64.b64decode(auth_data["authorizationToken"]).decode("utf-8")
            parts = token.split(":", 1)
            if len(parts) != 2:
                raise RuntimeError(
                    "Failed to get login token: malformed authorization token"
                )
            username, password = parts
            endpoint = auth_data["proxyEndpoint"]
            return {"username": username, "password": password, "endpoint": endpoint}
        except (ClientError, KeyError, IndexError, binascii.Error, UnicodeDecodeError) as e:
            raise RuntimeError(f"Failed to get login token: {e}") from e

    def set_lifecycle_policy(self, repo_name, max_image_count=100):
        if not isinstance(max_image_count, int) or max_image_count < 1:
            raise ValueError(
                f"max_image_count must be a positive integer, got {max_image_count!r}"
            )
        policy = json.dumps({
            "rules": [{
                "rulePriority": 1,
                "description": f"Keep last {max_image_count} images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": max_image_count,
                },
                "action": {"type": "expire"},
            }]
        })
        try:
            self.client.put_lifecycle_policy(
                repositoryName=repo_name, lifecyclePolicyText=policy
            )
            return True
        except ClientError as e:
            raise RuntimeError(
                f"Failed to set lifecycle policy for '{repo_name}': {e}"
            ) from e

    def get_image_uri(self, repo_name, tag="latest"):
        repo = self.describe_repository(repo_name)
        if not repo:
            raise ValueError(f"Repository '{repo_name}' not found")
        return f"{repo['repositoryUri']}:{tag}"

    def batch_delete_images(self, repo_name, image_ids):
        if not image_ids:
            return {"successes": [], "failures": []}
        try:
            response = self.client.batch_delete_image(
                repositoryName=repo_name, imageIds=image_ids
            )
            return {
                "successes": response.get("imageIds", []),
                "failures": response.get("failures", []),
            }
        except ClientError as e:
            raise RuntimeError(f"Failed to batch delete images: {e}") from e

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
