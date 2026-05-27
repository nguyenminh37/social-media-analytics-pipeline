#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-local}
NS=social-media-analytics

cd "$(dirname "$0")/.."

kubectl apply -k k8s
kubectl set image -n "$NS" deployment/social-media-spark "spark=social-media-spark:${TAG}"
kubectl rollout status -n "$NS" deployment/social-media-spark

printf 'spark image: social-media-spark:%s\n' "$TAG"
