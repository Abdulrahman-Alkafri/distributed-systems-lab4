#!/bin/bash
# Makes the app reachable from your laptop at https://192.168.122.250:30443
#
# Why this is needed: minikube runs inside a Docker container on the VM, so its
# NodePort (30443) only exists on the minikube IP (192.168.49.2) inside the VM.
# port-forward bridges the VM's own ports to the Nginx pod.
#
# ONE-TIME SETUP: the VM's firewall blocks these ports. Already done, but if
# you ever get "This site can't be reached / ERR_CONNECTION_TIMED_OUT", run:
#   sudo ufw allow 30443/tcp
#   sudo ufw allow 30080/tcp
#
# Keep this running while you use the app. Press Ctrl+C to stop.
echo "Open in your browser:  https://192.168.122.250:30443"
echo "(accept the self-signed certificate warning)"
kubectl port-forward --address 0.0.0.0 service/nginx 30443:443 30080:80
