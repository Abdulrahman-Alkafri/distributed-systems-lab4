# Distributed Systems Lab 4 — Kubernetes (Minikube)

Event-driven microservices on a single-node Kubernetes cluster:
Nginx → Flask (3 pods) → Redpanda (3 brokers) → two consumer workers → Redis.

## Files

| Path | What it is |
|---|---|
| `app/` | The Python code (Flask producer, counter worker, audit worker) |
| `k8s/01-redis.yaml` | Redis Deployment + PVC + Service |
| `k8s/02-redpanda.yaml` | Redpanda **StatefulSet** (3 brokers, one disk each) + 2 Services |
| `k8s/03-topics-job.yaml` | One-time **Job**: creates `visits-topic` (3 partitions × 3 replicas) and `visits-dlq` |
| `k8s/04-flask.yaml` | Flask **Deployment** (3 replicas) + headless Service |
| `k8s/05-workers.yaml` | counter-worker and audit-worker Deployments |
| `k8s/06-nginx.yaml` | Nginx ConfigMap + Deployment + **NodePort** Service |
| `deploy.sh` | Builds the image, creates the TLS secret, applies everything |
| `expose.sh` | Opens the app to your laptop at `https://192.168.122.250:30443` |
| `kubectl-commands.txt` | Cheat sheet of every command, including the DLQ and chaos tests |
| `docs/k8s-concepts.pdf` | Explains Pods, ReplicaSets, Deployments, StatefulSets, Services, Ingress |

## Deploy on the VM

```bash
ssh -p 2222 zaza@192.168.122.250
cd ~/lab4
git pull
./deploy.sh
```

Then, in a second terminal:

```bash
cd ~/lab4 && ./expose.sh
```

Open <https://192.168.122.250:30443> and accept the self-signed certificate.

## Notes

- The TLS certificate is generated on the VM by `deploy.sh` and is **not** stored in Git.
- The app image is built locally and pushed into the cluster with `minikube image load`,
  so the manifests use `imagePullPolicy: Never` and nothing is pulled from Docker Hub.
- Minikube is started with `--memory=3000mb --cpus=2` to fit the 4 GB VM, and every pod
  has explicit memory requests/limits.
