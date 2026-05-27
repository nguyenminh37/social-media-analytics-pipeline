#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-local}

cd "$(dirname "$0")/.."

docker build -f docker/Dockerfile.spark -t "social-media-spark:${TAG}" .
docker build -f docker/Dockerfile.collector -t "social-media-collector:${TAG}" .
docker build -f docker/Dockerfile.frontend -t "social-media-frontend:${TAG}" .

minikube image load "social-media-spark:${TAG}"
minikube image load "social-media-collector:${TAG}"
minikube image load "social-media-frontend:${TAG}"

printf 'loaded images with tag: %s\n' "$TAG"
