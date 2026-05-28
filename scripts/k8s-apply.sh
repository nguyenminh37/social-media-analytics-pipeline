#!/usr/bin/env bash
set -euo pipefail

TAG=${IMAGE_TAG:-stable-demo}
NS=social-media-analytics

cd "$(dirname "$0")/.."

load_youtube_api_key() {
  if [[ -n "${YOUTUBE_API_KEY:-}" ]]; then
    printf '%s' "$YOUTUBE_API_KEY"
    return
  fi
  if [[ -f .env ]]; then
    grep -m1 '^YOUTUBE_API_KEY=' .env | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true
  fi
}

ensure_youtube_secret() {
  local api_key
  api_key=$(load_youtube_api_key)
  if [[ -z "$api_key" ]]; then
    printf 'error: set YOUTUBE_API_KEY in the environment or .env before deploying k8s/youtube-producer-deployment.yaml\n' >&2
    exit 1
  fi
  kubectl apply -f k8s/namespace.yaml
  kubectl create secret generic youtube-api-key \
    -n "$NS" \
    --from-literal=YOUTUBE_API_KEY="$api_key" \
    --dry-run=client \
    -o yaml | kubectl apply -f -
}

delete_replayable_jobs() {
  kubectl delete -n "$NS" job/minio-bootstrap job/elasticsearch-kibana-smoke-check --ignore-not-found
}

app_deployments=(
  social-media-spark
  social-media-spark-youtube
  social-media-youtube-producer
  social-media-news-rss
  social-media-youtube-rss
  social-media-raw-archiver
  social-media-sentiment-enricher
  social-media-serving-api
  social-media-frontend
)

ensure_youtube_secret
delete_replayable_jobs
kubectl apply -k k8s
kubectl delete -n "$NS" deployment/social-media-ai-briefing --ignore-not-found
kubectl set image -n "$NS" deployment/social-media-spark "spark=social-media-spark:${TAG}"
kubectl set image -n "$NS" deployment/social-media-spark-youtube "spark=social-media-spark:${TAG}"
kubectl set image -n "$NS" deployment/social-media-youtube-producer "youtube-producer=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-news-rss "collector=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-youtube-rss "collector=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-raw-archiver "archiver=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-sentiment-enricher "sentiment-enricher=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-serving-api "serving-api=social-media-collector:${TAG}"
kubectl set image -n "$NS" deployment/social-media-frontend "frontend=social-media-frontend:${TAG}"

for deployment in "${app_deployments[@]}"; do
  kubectl rollout restart -n "$NS" "deployment/${deployment}"
done

for deployment in "${app_deployments[@]}"; do
  kubectl rollout status -n "$NS" "deployment/${deployment}"
done

printf 'spark image: social-media-spark:%s\n' "$TAG"
printf 'collector image: social-media-collector:%s\n' "$TAG"
printf 'frontend image: social-media-frontend:%s\n' "$TAG"
