from flask import Response
from flask_restful import Resource
import json
from utils.subscribe_manager import get_pubsub

class PaymentSubscribe(Resource):
    def get(self, request_id):
        def stream():
            q = get_pubsub(request_id)
            while True:
                msg = q.get()  # waits until backend pushes an update
                yield f"data: {json.dumps(msg)}\n\n"

        return Response(stream(), mimetype="text/event-stream")
