"""Tests for health check utilities."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.utils.health_check import HealthChecker


@pytest.fixture
def checker():
    return HealthChecker(timeout=1, retries=2, retry_delay=0)


class TestCheckHTTP:
    def test_healthy_endpoint(self, checker):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"status":"ok"}'

        with patch("src.utils.health_check.urlopen", return_value=mock_response):
            result = checker.check_http("http://localhost:5000/health")
            assert result["healthy"] is True
            assert result["status_code"] == 200
            assert result["attempts"] == 1

    def test_unhealthy_status_code(self, checker):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 503
        mock_response.read.return_value = b"Service Unavailable"

        with patch("src.utils.health_check.urlopen", return_value=mock_response):
            result = checker.check_http("http://localhost:5000/health")
            assert result["healthy"] is False
            assert result["status_code"] == 503

    def test_connection_error_retries(self, checker):
        from urllib.error import URLError

        with patch(
            "src.utils.health_check.urlopen",
            side_effect=URLError("Connection refused"),
        ):
            result = checker.check_http("http://localhost:5000/health")
            assert result["healthy"] is False
            assert result["attempts"] == 2
            assert "error" in result

    def test_timeout_error(self, checker):
        with patch(
            "src.utils.health_check.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            result = checker.check_http("http://localhost:5000/health")
            assert result["healthy"] is False
            assert result["attempts"] == 2

    def test_custom_expected_status(self, checker):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = b"Created"

        with patch("src.utils.health_check.urlopen", return_value=mock_response):
            result = checker.check_http("http://localhost/create", expected_status=201)
            assert result["healthy"] is True


class TestCheckTCP:
    def test_successful_connection(self, checker):
        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_socket_cls.return_value = mock_sock

            result = checker.check_tcp("localhost", 5000)
            assert result["healthy"] is True
            assert result["host"] == "localhost"
            assert result["port"] == 5000

    def test_connection_refused(self, checker):
        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 111
            mock_socket_cls.return_value = mock_sock

            result = checker.check_tcp("localhost", 9999)
            assert result["healthy"] is False
            assert "error" in result
            assert result["attempts"] == 2

    def test_socket_error(self, checker):
        import socket

        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.side_effect = socket.error("Network unreachable")
            mock_socket_cls.return_value = mock_sock

            result = checker.check_tcp("unreachable", 80)
            assert result["healthy"] is False
            assert result["attempts"] == 2

    def test_os_error(self, checker):
        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.side_effect = OSError("OS error")
            mock_socket_cls.return_value = mock_sock

            result = checker.check_tcp("host", 80)
            assert result["healthy"] is False


class TestCheckECSService:
    def test_healthy_service(self, checker):
        mock_client = MagicMock()
        mock_client.describe_services.return_value = {
            "services": [{
                "status": "ACTIVE",
                "runningCount": 2,
                "desiredCount": 2,
                "deployments": [{"status": "PRIMARY"}],
            }]
        }
        result = checker.check_ecs_service(mock_client, "cluster", "svc")
        assert result["healthy"] is True
        assert result["running_count"] == 2

    def test_unhealthy_service(self, checker):
        mock_client = MagicMock()
        mock_client.describe_services.return_value = {
            "services": [{
                "status": "ACTIVE",
                "runningCount": 0,
                "desiredCount": 2,
                "deployments": [],
            }]
        }
        result = checker.check_ecs_service(mock_client, "cluster", "svc")
        assert result["healthy"] is False

    def test_service_not_found(self, checker):
        mock_client = MagicMock()
        mock_client.describe_services.return_value = {"services": []}
        result = checker.check_ecs_service(mock_client, "cluster", "nonexistent")
        assert result["healthy"] is False
        assert "error" in result

    def test_service_check_client_error(self, checker):
        mock_client = MagicMock()
        mock_client.describe_services.side_effect = ClientError(
            {"Error": {"Code": "ClusterNotFoundException", "Message": "not found"}},
            "DescribeServices",
        )
        result = checker.check_ecs_service(mock_client, "cluster", "svc")
        assert result["healthy"] is False
        assert "error" in result

    def test_service_check_unexpected_error_propagates(self, checker):
        mock_client = MagicMock()
        mock_client.describe_services.side_effect = TypeError("unexpected")
        with pytest.raises(RuntimeError, match="Unexpected response from ECS API"):
            checker.check_ecs_service(mock_client, "cluster", "svc")


class TestBuildHealthCheckConfig:
    def test_default_config(self):
        config = HealthChecker.build_health_check_config(
            "curl -f http://localhost/health || exit 1"
        )
        assert config["command"] == [
            "CMD-SHELL", "curl -f http://localhost/health || exit 1"
        ]
        assert config["interval"] == 30
        assert config["timeout"] == 5
        assert config["retries"] == 3
        assert config["startPeriod"] == 60

    def test_custom_config(self):
        config = HealthChecker.build_health_check_config(
            "curl -f http://localhost/health",
            interval=60, timeout=10, retries=5, start_period=120,
        )
        assert config["interval"] == 60
        assert config["timeout"] == 10
        assert config["retries"] == 5
        assert config["startPeriod"] == 120

    def test_list_command(self):
        config = HealthChecker.build_health_check_config(
            ["CMD", "/bin/health-check"]
        )
        assert config["command"] == ["CMD", "/bin/health-check"]

    def test_empty_command(self):
        with pytest.raises(ValueError, match="command is required"):
            HealthChecker.build_health_check_config("")

    def test_invalid_interval(self):
        with pytest.raises(ValueError, match="Interval must be between"):
            HealthChecker.build_health_check_config("cmd", interval=1)

    def test_invalid_timeout(self):
        with pytest.raises(ValueError, match="Timeout must be between"):
            HealthChecker.build_health_check_config("cmd", timeout=1)

    def test_invalid_retries(self):
        with pytest.raises(ValueError, match="Retries must be between"):
            HealthChecker.build_health_check_config("cmd", retries=0)

    def test_invalid_start_period(self):
        with pytest.raises(ValueError, match="Start period must be between"):
            HealthChecker.build_health_check_config("cmd", start_period=500)


class TestGenerateHealthEndpointConfig:
    def test_default_config(self):
        config = HealthChecker.generate_health_endpoint_config()
        assert config["path"] == "/health"
        assert config["port"] == 80
        assert "curl" in config["command"]

    def test_custom_config(self):
        config = HealthChecker.generate_health_endpoint_config(
            path="/api/health", port=8080
        )
        assert config["path"] == "/api/health"
        assert config["port"] == 8080
        assert "8080" in config["command"]

    def test_invalid_path(self):
        with pytest.raises(ValueError, match="must start with /"):
            HealthChecker.generate_health_endpoint_config(path="health")

    def test_invalid_port(self):
        with pytest.raises(ValueError, match="Port must be between"):
            HealthChecker.generate_health_endpoint_config(port=0)

    def test_invalid_port_too_high(self):
        with pytest.raises(ValueError, match="Port must be between"):
            HealthChecker.generate_health_endpoint_config(port=70000)
