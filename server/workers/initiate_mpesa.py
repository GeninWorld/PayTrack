# workers/initiate_mpesa.py

import logging
from dotenv import load_dotenv
from models import ApiCollection, db
import requests
import base64
import re
from datetime import datetime
from flask import current_app
import os

from celery_app import celery

# M-Pesa API credentials (loaded from .env file)
MPESA_SHORTCODE = os.getenv("SAFARICOM_SANDBOX_SHORTCODE")
MPESA_PASSKEY = os.getenv("SAFARICOM_SANDBOX_PASSKEY")
MPESA_CONSUMER_KEY = os.getenv("SAFARICOM_SANDBOX_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("SAFARICOM_SANDBOX_CONSUMER_SECRET")

# URLs
MPESA_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
MPESA_AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

load_dotenv()
logger = logging.getLogger(__name__)


@celery.task(bind=True, name="workers.initiate_stk", max_retries=3, default_retry_delay=30)
def initiate_payment(self, api_collection_id):
    logger.info(f"Initiating payment for request {api_collection_id}")

    with current_app.app_context():
        api_collection = ApiCollection.query.get(api_collection_id)
        if not api_collection:
            logger.error(f"ApiCollection with ID {api_collection_id} not found.")
            return

        phone_number = api_collection.mpesa_number
        amount = api_collection.amount
        tenant_id = api_collection.tenant_id
        call_back_url = f"https://bgrtfdl5-5000.uks1.devtunnels.ms/payment/mpesa/call_back/{tenant_id}/{api_collection_id}"

        if not phone_number or not amount:
            logger.error(f"Missing phone number or amount for ApiCollection {api_collection_id}.")
            return

        def format_phone_number(number):
            digits = re.sub(r'\D', '', number)
            if re.match(r'^254\d{9}$', digits):
                return digits
            if re.match(r'^0[17]\d{8}$', digits):
                return '254' + digits[1:]
            logger.warning(f"Invalid phone number format: {number}")
            return None

        formatted_number = format_phone_number(phone_number)
        if not formatted_number:
            logger.error(f"Failed to format phone number: {phone_number}")
            return

        auth_token = get_mpesa_auth_token()
        if not auth_token:
            logger.error("Failed to get M-Pesa authorization token.")
            return

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        combined_string = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(combined_string.encode()).decode()

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(int(amount)),
            "PartyA": formatted_number,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": formatted_number,
            "CallBackURL": call_back_url,
            "AccountReference": "DUOTASKS.COM",
            "TransactionDesc": "Wallet Funding"
        }

        try:
            response = requests.post(MPESA_URL, headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}, json=payload)
            response_data = response.json()
            if response.status_code == 200:
                api_collection.mpesa_checkout_request_id = response_data.get("CheckoutRequestID")
                api_collection.status = "initiated"
                db.session.commit()
                logger.info(f"Payment request {api_collection_id} successfully initiated: {response_data}")
            else:
                logger.error(f"Failed to initiate payment for {api_collection_id}: {response_data}")
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error initiating payment for {api_collection_id}: {e}")


def get_mpesa_auth_token():
    auth = base64.b64encode(f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {auth}"}
    try:
        response = requests.get(MPESA_AUTH_URL, headers=headers)
        if response.status_code == 200:
            return response.json().get("access_token")
        logger.error(f"Failed to get auth token, status code: {response.status_code}, response: {response.text}")
        return None
    except Exception as e:
        logger.exception(f"Exception while fetching auth token: {e}")
        return None
