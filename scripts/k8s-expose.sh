#!/usr/bin/env bash
set -euo pipefail

NS=social-media-analytics

kubectl port-forward -n "$NS" svc/social-media-kibana 15601:5601 &
kubectl port-forward -n "$NS" svc/social-media-kafka-ui 8080:8080 &
kubectl port-forward -n "$NS" svc/social-media-minio 9001:9001 &
kubectl port-forward -n "$NS" svc/social-media-elasticsearch 9201:9200 &

wait
