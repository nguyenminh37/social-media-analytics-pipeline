#!/usr/bin/env bash
set -euo pipefail

NS=social-media-analytics
FRONTEND_NODE_PORT=${FRONTEND_NODE_PORT:-32001}
PUBLIC_INTERFACE=${PUBLIC_INTERFACE:-$(ip route show default | awk '{print $5; exit}')}
PUBLIC_IP=${PUBLIC_IP:-$(ip -4 addr show "$PUBLIC_INTERFACE" | awk '/inet / {sub(/\/.*/, "", $2); print $2; exit}')}
MINIKUBE_IP=${MINIKUBE_IP:-$(minikube ip)}

sysctl -w net.ipv4.ip_forward=1 >/dev/null

if command -v ufw >/dev/null 2>&1; then
  ufw allow "${FRONTEND_NODE_PORT}/tcp" >/dev/null || true
fi

iptables -t nat -C PREROUTING -p tcp -i "$PUBLIC_INTERFACE" --dport "$FRONTEND_NODE_PORT" \
  -j DNAT --to-destination "${MINIKUBE_IP}:${FRONTEND_NODE_PORT}" 2>/dev/null || \
  iptables -t nat -A PREROUTING -p tcp -i "$PUBLIC_INTERFACE" --dport "$FRONTEND_NODE_PORT" \
    -j DNAT --to-destination "${MINIKUBE_IP}:${FRONTEND_NODE_PORT}"
iptables -t nat -C OUTPUT -p tcp -d "$PUBLIC_IP" --dport "$FRONTEND_NODE_PORT" \
  -j DNAT --to-destination "${MINIKUBE_IP}:${FRONTEND_NODE_PORT}" 2>/dev/null || \
  iptables -t nat -A OUTPUT -p tcp -d "$PUBLIC_IP" --dport "$FRONTEND_NODE_PORT" \
    -j DNAT --to-destination "${MINIKUBE_IP}:${FRONTEND_NODE_PORT}"
iptables -t nat -C POSTROUTING -p tcp -d "$MINIKUBE_IP" --dport "$FRONTEND_NODE_PORT" \
  -j MASQUERADE 2>/dev/null || \
  iptables -t nat -A POSTROUTING -p tcp -d "$MINIKUBE_IP" --dport "$FRONTEND_NODE_PORT" \
    -j MASQUERADE
iptables -C FORWARD -p tcp -d "$MINIKUBE_IP" --dport "$FRONTEND_NODE_PORT" \
  -j ACCEPT 2>/dev/null || \
  iptables -I FORWARD 1 -p tcp -d "$MINIKUBE_IP" --dport "$FRONTEND_NODE_PORT" \
    -j ACCEPT
iptables -C FORWARD -p tcp -s "$MINIKUBE_IP" --sport "$FRONTEND_NODE_PORT" \
  -j ACCEPT 2>/dev/null || \
  iptables -I FORWARD 1 -p tcp -s "$MINIKUBE_IP" --sport "$FRONTEND_NODE_PORT" \
    -j ACCEPT

printf 'frontend: http://%s:%s\n' "$PUBLIC_IP" "$FRONTEND_NODE_PORT"

kubectl port-forward --address 0.0.0.0 -n "$NS" svc/social-media-kibana 15601:5601 &
kubectl port-forward --address 0.0.0.0 -n "$NS" svc/social-media-kafka-ui 8080:8080 &
kubectl port-forward --address 0.0.0.0 -n "$NS" svc/social-media-minio 9001:9001 &
kubectl port-forward --address 0.0.0.0 -n "$NS" svc/social-media-elasticsearch 9201:9200 &

wait
