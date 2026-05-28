#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-stable-demo}
CLEAN_MINIKUBE_IMAGE_CACHE=${CLEAN_MINIKUBE_IMAGE_CACHE:-true}

keep_current() {
  local image=$1
  docker images "$image" --format '{{.Repository}}:{{.Tag}} {{.ID}}' \
    | awk -v keep="${image}:${TAG}" '$1 != keep { print $2 }' \
    | sort -u \
    | xargs -r docker rmi
}

keep_current social-media-spark
keep_current social-media-collector
keep_current social-media-frontend

minikube ssh -- "docker images 'social-media-*' --format '{{.Repository}}:{{.Tag}} {{.ID}}'" \
  | awk -v tag=":${TAG}" '$1 !~ tag { print $2 }' \
  | sort -u \
  | xargs -r -I{} minikube ssh -- docker rmi {}

docker image prune -f
docker builder prune -f
minikube ssh -- docker container prune -f
minikube ssh -- docker image prune -f
minikube ssh -- docker builder prune -f

if [[ "$CLEAN_MINIKUBE_IMAGE_CACHE" == "true" ]]; then
  rm -rf "$HOME/.minikube/cache/images/amd64"/social-media-* 2>/dev/null || true
  minikube ssh -- "sudo rm -rf /var/lib/minikube/images/*social-media* 2>/dev/null || true"
fi

printf 'kept current app images with tag: %s\n' "$TAG"
