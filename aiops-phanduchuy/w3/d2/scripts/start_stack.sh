#!/usr/bin/env bash
set -e
echo "=== Starting AIOps Microservices Stack ==="
docker compose -f "$(dirname "$0")/../docker-compose.yml" up -d --build
echo "Waiting for pipeline /alerts endpoint to respond 200..."
timeout 120 bash -c 'until curl -sf http://localhost:8000/alerts?since=0 >/dev/null; do sleep 2; done'
echo "=== Stack Ready ==="
