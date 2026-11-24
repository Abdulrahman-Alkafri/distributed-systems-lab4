import json
import os
import signal

import redis
from confluent_kafka import Consumer, Producer

TOPIC = "visits-topic"
DLQ_TOPIC = "visits-dlq"
BROKERS = os.environ["KAFKA_BROKERS"]

r = redis.Redis(host=os.environ["REDIS_HOST"], port=6379, decode_responses=True)
dlq = Producer({"bootstrap.servers": BROKERS, "acks": "all"})

consumer = Consumer({
    "bootstrap.servers": BROKERS,
    "group.id": "counter-group",
    "auto.offset.reset": "earliest",
    "enable.auto.offset.store": False,   # mark a message done only AFTER we processed it
})


def on_assign(consumer, partitions):
    print(f"counter-group: this worker now owns partitions {[p.partition for p in partitions]}")


consumer.subscribe([TOPIC], on_assign=on_assign)
open("/tmp/healthy", "w").close()
print(f"Counter worker listening on '{TOPIC}' (group counter-group)...")

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

    where = f"[P{msg.partition()} @ offset {msg.offset()}]"
    try:
        data = json.loads(msg.value())
        container_id = data["container_id"]
        if not container_id:
            raise KeyError("container_id")
    except (ValueError, KeyError, TypeError) as e:
        # Malformed payload -> Dead Letter Queue, then keep going
        dlq.produce(DLQ_TOPIC, key=msg.key(), value=msg.value(), headers={
            "error": repr(e),
            "source": f"{TOPIC}/{msg.partition()}/{msg.offset()}",
        })
        dlq.flush(10)
        print(f"{where} MALFORMED {msg.value()!r} -> sent to {DLQ_TOPIC} ({e!r})")
    else:
        # Update both counters in one Redis transaction
        pipe = r.pipeline()
        pipe.incr("global_visits")
        pipe.hincrby("node_visits", container_id, 1)
        pipe.hset("node_partition", container_id, msg.partition())
        total, node, _ = pipe.execute()
        print(f"{where} visit from {container_id} -> node={node}, global={total}")

    consumer.store_offsets(msg)   # committed to the group automatically every 5s

consumer.close()   # commits stored offsets and leaves the group, so a rebalance happens right away
print("Counter worker stopped cleanly")
