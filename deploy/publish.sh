#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Bootstrap Argo CD. Website changes are published by pushing to main.
kubectl -n argocd apply -f deploy/argocd-application.yaml
