"""Service health checking utilities."""

import logging
import time
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self, timeout=5, retries=3, retry_delay=2):
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay

    def check_http(self, url, expected_status=200):
        last_error = None
        for attempt in range(self.retries):
            try:
                response = urlopen(url, timeout=self.timeout)  # noqa: S310
                status = response.getcode()
                body = response.read().decode("utf-8")
                return {
                    "healthy": status == expected_status,
                    "status_code": status,
                    "body": body,
                    "attempts": attempt + 1,
                }
            except (URLError, TimeoutError) as e:
                last_error = str(e)
                if attempt < self.retries - 1:
                    time.sleep(self.retry_delay)

        return {
            "healthy": False,
            "error": last_error,
            "attempts": self.retries,
        }

    def check_tcp(self, host, port):
        import socket

        last_error = None
        for attempt in range(self.retries):
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return {
                        "healthy": True,
                        "host": host,
                        "port": port,
                        "attempts": attempt + 1,
                    }
                last_error = f"Connection refused (code: {result})"
            except (socket.error, OSError) as e:
                last_error = str(e)
            finally:
                if sock is not None:
                    sock.close()

            if attempt < self.retries - 1:
                time.sleep(self.retry_delay)

        return {
            "healthy": False,
            "host": host,
            "port": port,
            "error": last_error,
            "attempts": self.retries,
        }

    def check_ecs_service(self, ecs_client, cluster, service_name):
        from botocore.exceptions import ClientError

        try:
            response = ecs_client.describe_services(
                cluster=cluster, services=[service_name]
            )
            services = response.get("services", [])
            if not services:
                return {"healthy": False, "error": "Service not found"}

            service = services[0]
            running = service.get("runningCount", 0)
            desired = service.get("desiredCount", 0)
            status = service.get("status", "UNKNOWN")

            return {
                "healthy": running == desired and running > 0 and status == "ACTIVE",
                "status": status,
                "running_count": running,
                "desired_count": desired,
                "deployments": len(service.get("deployments", [])),
            }
        except ClientError as e:
            logger.error("AWS API error checking service '%s': %s", service_name, e)
            return {"healthy": False, "error": str(e)}
        except (KeyError, TypeError) as e:
            logger.error(
                "Unexpected response structure checking service '%s': %s", service_name, e
            )
            raise RuntimeError(
                f"Unexpected response from ECS API for service '{service_name}': {e}"
            ) from e

    @staticmethod
    def build_health_check_config(
        command, interval=30, timeout=5, retries=3, start_period=60,
    ):
        if not command:
            raise ValueError("Health check command is required")
        if interval < 5 or interval > 300:
            raise ValueError("Interval must be between 5 and 300 seconds")
        if timeout < 2 or timeout > 60:
            raise ValueError("Timeout must be between 2 and 60 seconds")
        if retries < 1 or retries > 10:
            raise ValueError("Retries must be between 1 and 10")
        if start_period < 0 or start_period > 300:
            raise ValueError("Start period must be between 0 and 300 seconds")

        if isinstance(command, str):
            command = ["CMD-SHELL", command]

        return {
            "command": command,
            "interval": interval,
            "timeout": timeout,
            "retries": retries,
            "startPeriod": start_period,
        }

    @staticmethod
    def generate_health_endpoint_config(path="/health", port=80):
        if not path.startswith("/"):
            raise ValueError("Health check path must start with /")
        if port < 1 or port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        return {
            "path": path,
            "port": port,
            "command": f"curl -f http://localhost:{port}{path} || exit 1",
        }
