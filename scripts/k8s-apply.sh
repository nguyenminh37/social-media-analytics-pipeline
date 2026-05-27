#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-stable-demo}
NS=social-media-analytics

cd "$(dirname "$0")/.."

kubectl apply -k k8s
kubectl delete -n "$NS" deployment/social-media-ai-briefing --ignore-not-found
kubectl set image -n "$NS" deployment/social-media-spark "spark=social-media-spark:${TAG}"
kubectl set image -n "$NS" deployment/social-media-news-rss "collector=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-youtube-rss "collector=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-raw-archiver "archiver=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-sentiment-enricher "sentiment-enricher=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-serving-api "serving-api=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-frontend "frontend=social-media-frontend:${TAG}"
kubectl rollout restart -n "$NS" deployment/social-media-spark
kubectl rollout restart -n "$NS" deployment/social-media-news-rss
kubectl rollout restart -n "$NS" deployment/social-media-youtube-rss
kubectl rollout restart -n "$NS" deployment/social-media-raw-archiver
kubectl rollout restart -n "$NS" deployment/social-media-sentiment-enricher
kubectl rollout restart -n "$NS" deployment/social-media-serving-api
kubectl rollout restart -n "$NS" deployment/social-media-frontend
kubectl rollout status -n "$NS" deployment/social-media-spark
kubectl rollout status -n "$NS" deployment/social-media-news-rss
kubectl rollout status -n "$NS" deployment/social-media-youtube-rss
kubectl rollout status -n "$NS" deployment/social-media-raw-archiver
kubectl rollout status -n "$NS" deployment/social-media-sentiment-enricher
kubectl rollout status -n "$NS" deployment/social-media-serving-api
kubectl rollout status -n "$NS" deployment/social-media-frontend

printf 'spark image: social-media-spark:%s\n' "$TAG"
printf 'frontend image: social-media-frontend:%s\n' "$TAG"
