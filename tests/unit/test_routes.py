"""Tests for API routes - good coverage."""

import pytest

from src.app.main import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    def test_health_check_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_healthy(self, client):
        response = client.get("/health")
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "ecs-workshop"


class TestInfoEndpoint:
    def test_get_info_returns_200(self, client):
        response = client.get("/api/v1/info")
        assert response.status_code == 200

    def test_get_info_contains_app_name(self, client):
        data = client.get("/api/v1/info").get_json()
        assert data["application"] == "AWS ECS Workshop"
        assert data["version"] == "0.1.0"


class TestTasksEndpoint:
    def test_list_tasks_returns_all_tasks(self, client):
        response = client.get("/api/v1/tasks")
        data = response.get_json()
        assert data["total"] == 6
        assert len(data["tasks"]) == 6

    def test_get_task_returns_specific_task(self, client):
        response = client.get("/api/v1/tasks/1")
        data = response.get_json()
        assert data["id"] == 1
        assert data["name"] == "Build Docker Image"

    def test_get_nonexistent_task_returns_404(self, client):
        response = client.get("/api/v1/tasks/99")
        assert response.status_code == 404


class TestValidateEndpoint:
    def test_validate_valid_config(self, client):
        data = {"cluster_name": "test", "service_name": "svc", "image": "img:latest"}
        response = client.post("/api/v1/validate", json=data)
        assert response.status_code == 200
        assert response.get_json()["valid"] is True

    def test_validate_missing_fields(self, client):
        response = client.post("/api/v1/validate", json={"cluster_name": "test"})
        assert response.status_code == 400
        data = response.get_json()
        assert data["valid"] is False

    def test_validate_empty_body(self, client):
        response = client.post("/api/v1/validate", content_type="application/json")
        assert response.status_code == 400
