import json
import os
import socket
import time

import redis
from confluent_kafka import Producer
from flask import Flask, Response, render_template_string, request

TOPIC = "visits-topic"
CONTAINER_ID = socket.gethostname()

app = Flask(__name__)
r = redis.Redis(host=os.environ["REDIS_HOST"], port=6379, decode_responses=True)
producer = Producer({
    "bootstrap.servers": os.environ["KAFKA_BROKERS"],   # all 3 brokers, so any one can be down
    "acks": "all",                 # leader confirms only after the replicas have it
    "enable.idempotence": True,    # retries during a leader election never create duplicates
})

PAGE = """
<html><head><title>Lab 4</title></head>
<body style="font-family:sans-serif;text-align:center;margin-top:60px">
  <h1>Event-Driven Visit Counter</h1>
  <h2>Pod Name: {{ cid }}</h2>
  <h2>Node Visits: <span id="node">{{ node }}</span></h2>
  <h2>Global Visits: <span id="global">{{ total }}</span></h2>
  <h3>Kafka partition for this container: <span id="partition">{{ partition }}</span></h3>
  <p id="status" style="color:gray">connecting to live updates...</p>
  <script>
    // SSE: the browser keeps one connection open and the server pushes new counters every second
    const es = new EventSource("/stream?cid={{ cid }}");
    es.onmessage = (e) => {
      const d = JSON.parse(e.data);
      document.getElementById("node").textContent = d.node;
      document.getElementById("global").textContent = d.global;
      document.getElementById("partition").textContent = d.partition;
      document.getElementById("status").textContent = "live (updated " + new Date().toLocaleTimeString() + ")";
    };
    es.onerror = () => { document.getElementById("status").textContent = "reconnecting..."; };
  </script>
</body></html>
"""


def counters(cid):
    return {
        "global": int(r.get("global_visits") or 0),
        "node": int(r.hget("node_visits", cid) or 0),
        "partition": r.hget("node_partition", cid) or "-",
    }


@app.route("/")
def index():
    # READ path: just read the counters from Redis
    c = counters(CONTAINER_ID)

    # WRITE path: don't touch Redis, publish an event with key = container_id (async)
    event = json.dumps({"container_id": CONTAINER_ID, "ts": time.time()})
    producer.produce(TOPIC, key=CONTAINER_ID, value=event)
    producer.poll(0)

    return render_template_string(PAGE, cid=CONTAINER_ID, node=c["node"],
                                  total=c["global"], partition=c["partition"])


@app.route("/stream")
def stream():
    # Server-Sent Events: push this container's counters once per second
    cid = request.args.get("cid", CONTAINER_ID)

    def events():
        while True:
            yield f"data: {json.dumps(counters(cid))}\n\n"
            time.sleep(1)

    return Response(events(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/health")
def health():
    return "OK"
