#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-local}
IMAGE_ARCHIVE_DIR=$(mktemp -d)

cd "$(dirname "$0")/.."

cleanup() {
  rm -rf "$IMAGE_ARCHIVE_DIR"
}
trap cleanup EXIT

docker build -f docker/Dockerfile.spark -t "social-media-spark:${TAG}" .
docker build -f docker/Dockerfile.collector -t "social-media-collector:${TAG}" .
docker build -f docker/Dockerfile.frontend -t "social-media-frontend:${TAG}" .

docker save "social-media-spark:${TAG}" -o "$IMAGE_ARCHIVE_DIR/social-media-spark.tar"
docker save "social-media-collector:${TAG}" -o "$IMAGE_ARCHIVE_DIR/social-media-collector.tar"
docker save "social-media-frontend:${TAG}" -o "$IMAGE_ARCHIVE_DIR/social-media-frontend.tar"

minikube image load --overwrite=true "$IMAGE_ARCHIVE_DIR/social-media-spark.tar"
minikube image load --overwrite=true "$IMAGE_ARCHIVE_DIR/social-media-collector.tar"
minikube image load --overwrite=true "$IMAGE_ARCHIVE_DIR/social-media-frontend.tar"

printf 'loaded images with tag: %s\n' "$TAG"
