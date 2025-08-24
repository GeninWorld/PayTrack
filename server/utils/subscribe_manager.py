from flask import current_app
import json
from datetime import datetime

def get_pubsub(request_id):
    """
    Subscribe to a Redis channel named after the request_id.
    """
    r = current_app.redis
    pubsub = r.pubsub()
    pubsub.subscribe(f"request:{request_id}")
    return pubsub


def push_to_queue(request_id, status_msg: dict):
    """
    Publish status and logs in a single event.
    """
    r = current_app.redis

    event_payload = {
        "type": "transaction_event",
        "status": status_msg,
        "sent_at": datetime.utcnow().isoformat()
    }

    r.publish(f"request:{request_id}", json.dumps(event_payload))
