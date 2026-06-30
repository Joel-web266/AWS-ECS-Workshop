#!/bin/bash
set -euo pipefail

CLUSTER_NAME="${ECS_CLUSTER_NAME:-ecs-workshop-cluster}"
SERVICE_NAME="${ECS_SERVICE_NAME:-ecs-workshop-service}"
REGION="${AWS_REGION:-us-east-1}"

echo "Deploying to ECS cluster: ${CLUSTER_NAME}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"

aws ecs update-service \
    --cluster "${CLUSTER_NAME}" \
    --service "${SERVICE_NAME}" \
    --force-new-deployment \
    --region "${REGION}"

echo "Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster "${CLUSTER_NAME}" \
    --services "${SERVICE_NAME}" \
    --region "${REGION}"

echo "Deployment complete!"
