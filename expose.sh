#!/bin/bash
# Makes the app reachable from your laptop at https://192.168.122.250:30443
#
# Why this is needed: minikube runs inside a Docker container on the VM, so its
# NodePort (30443) only exists on the minikube IP (192.168.49.2) inside the VM.
# port-forward bridges the VM's own port 30443 to the Nginx pod.
#
# Keep this running while you use the app. Press Ctrl+C to stop.
echo "Open in your browser:  https://192.168.122.250:30443"
echo "(accept the self-signed certificate warning)"
kubectl port-forward --address 0.0.0.0 service/nginx 30443:443
