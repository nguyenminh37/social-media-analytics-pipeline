#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-local}
NS=social-media-analytics

cd "$(dirname "$0")/.."

kubectl apply -k k8s
kubectl set image -n "$NS" deployment/social-media-spark "spark=social-media-spark:${TAG}"
kubectl set image -n "$NS" deployment/social-media-news-rss "collector=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-youtube-rss "collector=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-raw-archiver "archiver=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-ai-briefing "ai-briefing=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-sentiment-enricher "sentiment-enricher=social-media-collector:${TAG}"
kubectl rollout status -n "$NS" deployment/social-media-spark
kubectl rollout status -n "$NS" deployment/social-media-news-rss
kubectl rollout status -n "$NS" deployment/social-media-youtube-rss
kubectl rollout status -n "$NS" deployment/social-media-raw-archiver
kubectl rollout status -n "$NS" deployment/social-media-ai-briefing
kubectl rollout status -n "$NS" deployment/social-media-sentiment-enricher

printf 'spark image: social-media-spark:%s\n' "$TAG"
