#!/bin/bash
set -euo pipefail

CLUSTER_NAME="${ECS_CLUSTER_NAME:-ecs-workshop-cluster}"
SERVICE_NAME="${ECS_SERVICE_NAME:-ecs-workshop-service}"
REGION="${AWS_REGION:-us-east-1}"

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "ERROR: Deployment failed with exit code ${exit_code}" >&2
        echo "  Cluster: ${CLUSTER_NAME}" >&2
        echo "  Service: ${SERVICE_NAME}" >&2
        echo "  Region:  ${REGION}" >&2
        echo "  Failed at line: ${BASH_LINENO[0]}" >&2
    fi
    exit $exit_code
}
trap cleanup EXIT

echo "Deploying to ECS cluster: ${CLUSTER_NAME}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"

echo "Triggering new deployment..."
if ! aws ecs update-service \
    --cluster "${CLUSTER_NAME}" \
    --service "${SERVICE_NAME}" \
    --force-new-deployment \
    --region "${REGION}" > /dev/null; then
    echo "ERROR: Failed to trigger deployment. Verify the cluster and service exist." >&2
    exit 1
fi

echo "Waiting for service to stabilize..."
if ! aws ecs wait services-stable \
    --cluster "${CLUSTER_NAME}" \
    --services "${SERVICE_NAME}" \
    --region "${REGION}"; then
    echo "ERROR: Service did not stabilize within the expected time." >&2
    echo "Check the ECS console for deployment events and task failures." >&2
    exit 1
fi

echo "Deployment complete!"
