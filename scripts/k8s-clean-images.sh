#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-local}

keep_current() {
  local image=$1
  docker images "$image" --format '{{.Repository}}:{{.Tag}} {{.ID}}' \
    | awk -v keep="${image}:${TAG}" '$1 != keep { print $2 }' \
    | sort -u \
    | xargs -r docker rmi
}

keep_current social-media-spark
keep_current social-media-collector

minikube ssh -- "docker images 'social-media-*' --format '{{.Repository}}:{{.Tag}} {{.ID}}'" \
  | awk -v tag=":${TAG}" '$1 !~ tag { print $2 }' \
  | sort -u \
  | xargs -r -I{} minikube ssh -- docker rmi {}

printf 'kept current app images with tag: %s\n' "$TAG"
