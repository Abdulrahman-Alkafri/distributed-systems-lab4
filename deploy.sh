#!/bin/bash
# Deploy Lab 4 to minikube. Run this on the VM:  ./deploy.sh
set -e
cd "$(dirname "$0")"

echo "==> 1/4  Building the app image INSIDE minikube's docker"
# This makes "docker build" put the image where minikube can see it,
# so Kubernetes never has to download it from the internet.
eval "$(minikube docker-env)"
docker build -t lab4-app:1 ./app

echo "==> 2/4  Creating the TLS certificate secret (only the first time)"
# The certificate is generated HERE, not stored in git.
if ! kubectl get secret nginx-tls >/dev/null 2>&1; then
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout /tmp/tls.key -out /tmp/tls.crt -subj "/CN=lab4" 2>/dev/null
  kubectl create secret tls nginx-tls --cert=/tmp/tls.crt --key=/tmp/tls.key
else
  echo "    secret nginx-tls already exists, skipping"
fi

echo "==> 3/4  Applying all manifests"
kubectl apply -f k8s/

echo "==> 4/4  Waiting for everything to be ready (this takes a few minutes)"
kubectl rollout status statefulset/redpanda --timeout=300s
kubectl wait --for=condition=complete job/create-topics --timeout=300s
kubectl rollout status deployment/flask --timeout=180s
kubectl rollout status deployment/nginx --timeout=180s

echo
kubectl get pods
echo
echo "Done. Open the app with:   ./expose.sh"
