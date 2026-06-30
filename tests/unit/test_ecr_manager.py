"""Tests for ECR manager utilities."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from src.utils.ecr_manager import ECRManager


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


@pytest.fixture
def ecr_manager(mock_session):
    return ECRManager(region="us-east-1", session=mock_session)


class TestCreateRepository:
    def test_create_repository(self, ecr_manager):
        ecr_manager.client.create_repository.return_value = {
            "repository": {"repositoryName": "my-app", "repositoryUri": "123.ecr/my-app"}
        }
        result = ecr_manager.create_repository("my-app")
        assert result["repositoryName"] == "my-app"

    def test_create_repository_with_options(self, ecr_manager):
        ecr_manager.client.create_repository.return_value = {
            "repository": {"repositoryName": "my-app"}
        }
        ecr_manager.create_repository(
            "my-app", image_tag_mutability="IMMUTABLE", scan_on_push=True
        )
        call_kwargs = ecr_manager.client.create_repository.call_args[1]
        assert call_kwargs["imageTagMutability"] == "IMMUTABLE"
        assert call_kwargs["imageScanningConfiguration"]["scanOnPush"] is True

    def test_create_repository_already_exists(self, ecr_manager):
        ecr_manager.client.create_repository.side_effect = ClientError(
            {"Error": {"Code": "RepositoryAlreadyExistsException", "Message": "exists"}},
            "CreateRepository",
        )
        ecr_manager.client.describe_repositories.return_value = {
            "repositories": [{"repositoryName": "my-app"}]
        }
        result = ecr_manager.create_repository("my-app")
        assert result["repositoryName"] == "my-app"

    def test_create_repository_invalid_name(self, ecr_manager):
        with pytest.raises(ValueError, match="Invalid repository name"):
            ecr_manager.create_repository("INVALID-NAME")

    def test_create_repository_empty_name(self, ecr_manager):
        with pytest.raises(ValueError, match="Invalid repository name"):
            ecr_manager.create_repository("")

    def test_create_repository_client_error(self, ecr_manager):
        ecr_manager.client.create_repository.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "CreateRepository",
        )
        with pytest.raises(RuntimeError, match="Failed to create repository"):
            ecr_manager.create_repository("my-app")


class TestDeleteRepository:
    def test_delete_repository(self, ecr_manager):
        ecr_manager.client.delete_repository.return_value = {
            "repository": {"repositoryName": "my-app"}
        }
        result = ecr_manager.delete_repository("my-app")
        assert result["repositoryName"] == "my-app"

    def test_delete_repository_force(self, ecr_manager):
        ecr_manager.client.delete_repository.return_value = {
            "repository": {"repositoryName": "my-app"}
        }
        ecr_manager.delete_repository("my-app", force=True)
        ecr_manager.client.delete_repository.assert_called_once_with(
            repositoryName="my-app", force=True
        )

    def test_delete_repository_error(self, ecr_manager):
        ecr_manager.client.delete_repository.side_effect = ClientError(
            {"Error": {"Code": "RepositoryNotFoundException", "Message": "nope"}},
            "DeleteRepository",
        )
        with pytest.raises(RuntimeError, match="Failed to delete repository"):
            ecr_manager.delete_repository("nonexistent")


class TestDescribeRepository:
    def test_describe_repository(self, ecr_manager):
        ecr_manager.client.describe_repositories.return_value = {
            "repositories": [{"repositoryName": "my-app", "repositoryUri": "123/my-app"}]
        }
        result = ecr_manager.describe_repository("my-app")
        assert result["repositoryName"] == "my-app"

    def test_describe_repository_not_found(self, ecr_manager):
        ecr_manager.client.describe_repositories.side_effect = ClientError(
            {"Error": {"Code": "RepositoryNotFoundException", "Message": "nope"}},
            "DescribeRepositories",
        )
        result = ecr_manager.describe_repository("nonexistent")
        assert result is None

    def test_describe_repository_empty_result(self, ecr_manager):
        ecr_manager.client.describe_repositories.return_value = {"repositories": []}
        result = ecr_manager.describe_repository("empty")
        assert result is None

    def test_describe_repository_error(self, ecr_manager):
        ecr_manager.client.describe_repositories.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "DescribeRepositories",
        )
        with pytest.raises(RuntimeError, match="Failed to describe repository"):
            ecr_manager.describe_repository("my-app")


class TestListRepositories:
    def test_list_repositories(self, ecr_manager):
        ecr_manager.client.describe_repositories.return_value = {
            "repositories": [
                {"repositoryName": "app1"},
                {"repositoryName": "app2"},
            ]
        }
        result = ecr_manager.list_repositories()
        assert len(result) == 2

    def test_list_repositories_error(self, ecr_manager):
        ecr_manager.client.describe_repositories.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "DescribeRepositories",
        )
        with pytest.raises(RuntimeError, match="Failed to list repositories"):
            ecr_manager.list_repositories()


class TestListImages:
    def test_list_images(self, ecr_manager):
        ecr_manager.client.list_images.return_value = {
            "imageIds": [
                {"imageTag": "latest", "imageDigest": "sha256:abc"},
            ]
        }
        result = ecr_manager.list_images("my-app")
        assert len(result) == 1

    def test_list_images_error(self, ecr_manager):
        ecr_manager.client.list_images.side_effect = ClientError(
            {"Error": {"Code": "RepositoryNotFoundException", "Message": "nope"}},
            "ListImages",
        )
        with pytest.raises(RuntimeError, match="Failed to list images"):
            ecr_manager.list_images("nonexistent")


class TestGetLoginToken:
    def test_get_login_token(self, ecr_manager):
        import base64

        token = base64.b64encode(b"AWS:mypassword").decode("utf-8")
        ecr_manager.client.get_authorization_token.return_value = {
            "authorizationData": [{
                "authorizationToken": token,
                "proxyEndpoint": "https://123.dkr.ecr.us-east-1.amazonaws.com",
            }]
        }
        result = ecr_manager.get_login_token()
        assert result["username"] == "AWS"
        assert result["password"] == "mypassword"
        assert "amazonaws.com" in result["endpoint"]

    def test_get_login_token_error(self, ecr_manager):
        ecr_manager.client.get_authorization_token.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "GetAuthorizationToken",
        )
        with pytest.raises(RuntimeError, match="Failed to get login token"):
            ecr_manager.get_login_token()


class TestSetLifecyclePolicy:
    def test_set_lifecycle_policy(self, ecr_manager):
        ecr_manager.client.put_lifecycle_policy.return_value = {}
        result = ecr_manager.set_lifecycle_policy("my-app", max_image_count=50)
        assert result is True

    def test_set_lifecycle_policy_error(self, ecr_manager):
        ecr_manager.client.put_lifecycle_policy.side_effect = ClientError(
            {"Error": {"Code": "RepositoryNotFoundException", "Message": "nope"}},
            "PutLifecyclePolicy",
        )
        with pytest.raises(RuntimeError, match="Failed to set lifecycle policy"):
            ecr_manager.set_lifecycle_policy("nonexistent")


class TestGetImageUri:
    def test_get_image_uri(self, ecr_manager):
        ecr_manager.client.describe_repositories.return_value = {
            "repositories": [{
                "repositoryName": "my-app",
                "repositoryUri": "123456.dkr.ecr.us-east-1.amazonaws.com/my-app",
            }]
        }
        result = ecr_manager.get_image_uri("my-app", tag="v1.0")
        assert result == "123456.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0"

    def test_get_image_uri_not_found(self, ecr_manager):
        ecr_manager.client.describe_repositories.return_value = {"repositories": []}
        with pytest.raises(ValueError, match="not found"):
            ecr_manager.get_image_uri("nonexistent")


class TestBatchDeleteImages:
    def test_batch_delete_images(self, ecr_manager):
        ecr_manager.client.batch_delete_image.return_value = {
            "imageIds": [{"imageTag": "old"}],
            "failures": [],
        }
        result = ecr_manager.batch_delete_images(
            "my-app", [{"imageTag": "old"}]
        )
        assert len(result["successes"]) == 1
        assert len(result["failures"]) == 0

    def test_batch_delete_images_empty_list(self, ecr_manager):
        result = ecr_manager.batch_delete_images("my-app", [])
        assert result == {"successes": [], "failures": []}

    def test_batch_delete_images_error(self, ecr_manager):
        ecr_manager.client.batch_delete_image.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "BatchDeleteImage",
        )
        with pytest.raises(RuntimeError, match="Failed to batch delete"):
            ecr_manager.batch_delete_images("my-app", [{"imageTag": "x"}])


class TestIsValidRepoName:
    def test_valid_names(self):
        assert ECRManager._is_valid_repo_name("my-app") is True
        assert ECRManager._is_valid_repo_name("my/app") is True
        assert ECRManager._is_valid_repo_name("my.app") is True
        assert ECRManager._is_valid_repo_name("app123") is True

    def test_invalid_names(self):
        assert ECRManager._is_valid_repo_name("") is False
        assert ECRManager._is_valid_repo_name("My-App") is False
        assert ECRManager._is_valid_repo_name("-app") is False
        assert ECRManager._is_valid_repo_name(None) is False


class TestGetRepositoryPolicy:
    def test_get_repository_policy(self, ecr_manager):
        ecr_manager.client.get_repository_policy.return_value = {
            "policyText": '{"Version":"2012-10-17"}'
        }
        result = ecr_manager.get_repository_policy("my-app")
        assert "Version" in result

    def test_get_repository_policy_not_found(self, ecr_manager):
        ecr_manager.client.get_repository_policy.side_effect = ClientError(
            {"Error": {"Code": "RepositoryPolicyNotFoundException", "Message": "nope"}},
            "GetRepositoryPolicy",
        )
        result = ecr_manager.get_repository_policy("my-app")
        assert result is None

    def test_get_repository_policy_error(self, ecr_manager):
        ecr_manager.client.get_repository_policy.side_effect = ClientError(
            {"Error": {"Code": "ServerException", "Message": "fail"}},
            "GetRepositoryPolicy",
        )
        with pytest.raises(RuntimeError, match="Failed to get repository policy"):
            ecr_manager.get_repository_policy("my-app")
