"""API route handlers for the ECS Workshop application."""

from flask import Blueprint, jsonify, request

api = Blueprint("api", __name__)


@api.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "ecs-workshop"})


@api.route("/api/v1/info", methods=["GET"])
def get_info():
    return jsonify({
        "application": "AWS ECS Workshop",
        "version": "0.1.0",
        "description": "Hands-on ECS deployment workshop",
    })


@api.route("/api/v1/tasks", methods=["GET"])
def list_tasks():
    tasks = [
        {"id": 1, "name": "Build Docker Image", "module": 1, "completed": False},
        {"id": 2, "name": "Push to ECR", "module": 2, "completed": False},
        {"id": 3, "name": "Create ECS Cluster", "module": 3, "completed": False},
        {"id": 4, "name": "Deploy Service", "module": 4, "completed": False},
        {"id": 5, "name": "Configure Monitoring", "module": 5, "completed": False},
        {"id": 6, "name": "Set Up Health Checks", "module": 6, "completed": False},
    ]
    return jsonify({"tasks": tasks, "total": len(tasks)})


@api.route("/api/v1/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    tasks = {
        1: {"id": 1, "name": "Build Docker Image", "module": 1, "completed": False},
        2: {"id": 2, "name": "Push to ECR", "module": 2, "completed": False},
        3: {"id": 3, "name": "Create ECS Cluster", "module": 3, "completed": False},
        4: {"id": 4, "name": "Deploy Service", "module": 4, "completed": False},
        5: {"id": 5, "name": "Configure Monitoring", "module": 5, "completed": False},
        6: {"id": 6, "name": "Set Up Health Checks", "module": 6, "completed": False},
    }
    task = tasks.get(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@api.route("/api/v1/validate", methods=["POST"])
def validate_config():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=False)
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    errors = []
    required_fields = ["cluster_name", "service_name", "image"]
    for field_name in required_fields:
        if field_name not in data:
            errors.append(f"Missing required field: {field_name}")

    if errors:
        return jsonify({"valid": False, "errors": errors}), 400

    return jsonify({"valid": True, "message": "Configuration is valid"})
