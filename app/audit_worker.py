import json
import os
import signal
from datetime import datetime, timezone

from confluent_kafka import Consumer

TOPIC = "visits-topic"
LOG_FILE = "/app/logs/audit.log"

consumer = Consumer({
    "bootstrap.servers": os.environ["KAFKA_BROKERS"],
    "group.id": "audit-group",           # separate group = its own copy of every event
    "auto.offset.reset": "earliest",
})


def on_assign(consumer, partitions):
    print(f"audit-group: this worker now owns partitions {[p.partition for p in partitions]}")


consumer.subscribe([TOPIC], on_assign=on_assign)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
log = open(LOG_FILE, "a", buffering=1)   # line-buffered: every entry hits the file immediately
open("/tmp/healthy", "w").close()
print(f"Audit worker listening on '{TOPIC}' (group audit-group), writing {LOG_FILE}...")

# docker stop sends SIGTERM: finish the current message, then leave the group cleanly
running = True


def stop(*_):
    global running
    running = False


signal.signal(signal.SIGTERM, stop)

while running:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print("Kafka error:", msg.error())
        continue

    # Uses only Kafka metadata + key, so even malformed payloads get audited
    entry = {
        "timestamp": datetime.fromtimestamp(msg.timestamp()[1] / 1000, timezone.utc).isoformat(),
        "container_id": msg.key().decode() if msg.key() else None,
        "partition": msg.partition(),
        "offset": msg.offset(),
    }
    line = json.dumps(entry)
    print(line)
    log.write(line + "\n")

consumer.close()   # commits offsets and leaves the group
print("Audit worker stopped cleanly")
