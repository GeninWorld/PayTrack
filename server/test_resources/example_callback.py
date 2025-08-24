from flask_restful import Resource, request
import logging

logger = logging.getLogger(__name__)

class TestWebhookResource(Resource):
    def post(self):
        """
        Receives any POST request and prints/logs the payload.
        """
        data = request.get_json()  # JSON payload
        form_data = request.form.to_dict()  # form-encoded data
        headers = dict(request.headers)  # headers

        # Log to console
        print("=== Webhook Received ===")
        print("JSON:", data)
        print("Form Data:", form_data)
        print("Headers:", headers)
        print("=======================")

        # Optional: log with logging module
        logger.info(f"Webhook received: JSON={data}, Form={form_data}, Headers={headers}")

        # Respond with 200 OK
        return {"message": "Webhook received successfully"}, 200
