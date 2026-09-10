#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
kubectl -n media create configmap lina-quiz-site --from-file=web/index.html --from-file=web/style.css --from-file=web/quiz.js --from-file=web/app.js --from-file=questions.json --dry-run=client -o yaml > /tmp/lina-quiz-site.yaml
kubectl -n media apply -f /tmp/lina-quiz-site.yaml
kubectl -n media create configmap lina-quiz-nginx --from-file=default.conf=deploy/nginx.conf --dry-run=client -o yaml > /tmp/lina-quiz-nginx.yaml
kubectl -n media apply -f /tmp/lina-quiz-nginx.yaml
kubectl -n media apply -f deploy/kubernetes.yaml
kubectl -n media rollout restart deployment/lina-quiz
kubectl -n media rollout status deployment/lina-quiz --timeout=120s
