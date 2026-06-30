# AWS ECS Workshop

A hands-on workshop for deploying containerized applications on Amazon ECS (Elastic Container Service).

## Project Structure

```
├── src/
│   ├── app/              # Flask web application
│   │   ├── __init__.py
│   │   ├── main.py       # Application entry point
│   │   ├── routes.py     # API route handlers
│   │   └── models.py     # Data models
│   ├── utils/            # Utility modules
│   │   ├── __init__.py
│   │   ├── ecs_manager.py    # ECS cluster/service management
│   │   ├── ecr_manager.py    # ECR repository management
│   │   ├── cloudwatch.py     # CloudWatch logging/metrics
│   │   ├── task_definition.py # ECS task definition builder
│   │   └── health_check.py   # Service health checking
│   └── config/           # Configuration
│       ├── __init__.py
│       └── settings.py   # Application settings
├── tests/
│   └── unit/             # Unit tests
├── infrastructure/       # CloudFormation templates
├── scripts/              # Helper scripts
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

## Prerequisites

- Python 3.10+
- Docker
- AWS CLI configured with appropriate permissions
- An AWS account with ECS, ECR, and CloudWatch access

## Setup

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python -m src.app.main
```

## Running Tests

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Workshop Modules

1. **Module 1**: Building and containerizing the application
2. **Module 2**: Setting up ECR and pushing images
3. **Module 3**: Creating ECS clusters and task definitions
4. **Module 4**: Deploying services and configuring load balancing
5. **Module 5**: Monitoring with CloudWatch
6. **Module 6**: Health checks and auto-scaling
