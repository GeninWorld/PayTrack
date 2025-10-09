# workers/initiate_mpesa.py

import logging
from dotenv import load_dotenv
from models import ApiCollection, db, ApiDisbursement
import requests
import base64
import re
from datetime import datetime
from sqlalchemy.orm import joinedload
from flask import current_app
import os

from celery_app import celery
load_dotenv()

# M-Pesa API credentials (loaded from .env file)
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
B2C_URL = "https://api.safaricom.co.ke/mpesa/b2c/v3/paymentrequest"
B2B_URL = "https://api.safaricom.co.ke/mpesa/b2b/v1/paymentrequest"
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
INITIATOR_NAME = os.getenv("INITIATOR_NAME")
SECURITY_CREDENTIAL = os.getenv("SECURITY_CREDENTIAL")

# URLs
MPESA_URL = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
MPESA_AUTH_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
API_BASE_URL = os.getenv("API_BASE_URL", "https://rhtr3fc9-5000.uks1.devtunnels.ms")

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="workers.initiate_stk", max_retries=3, default_retry_delay=30)
def initiate_payment(self, api_collection_id):
    logger.info(f"Initiating payment for request {api_collection_id}")

    with current_app.app_context():
        api_collection = (
            ApiCollection.query
            .options(joinedload(ApiCollection.tenant))
            .get(api_collection_id)
        )       
        if not api_collection:
            logger.error(f"ApiCollection with ID {api_collection_id} not found.")
            return

        phone_number = api_collection.mpesa_number
        tenant_name = api_collection.tenant.name if api_collection.tenant else "Unknown"
        amount = api_collection.amount
        tenant_id = api_collection.tenant_id
        call_back_url = f"{API_BASE_URL}/payment/mpesa/call_back/{tenant_id}/{api_collection_id}"

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
            "AccountReference": tenant_name,
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




@celery.task(bind=True, name="workers.disbursment_initiate", max_retries=3, default_retry_delay=30)
def initiate_disbursement(self, api_disbursement_id):
    logger.info(f"Initiating disbursement for request {api_disbursement_id}")
    try:
        with current_app.app_context():
            api_disbursement = ApiDisbursement.query.get(api_disbursement_id)
            if not api_disbursement:
                logger.error(f"ApiDisbursement with ID {api_disbursement_id} not found.")
                return
            
            amount = api_disbursement.amount
            tenant_id = api_disbursement.tenant_id
            
            # Determine disbursement type and validate
            if api_disbursement.mpesa_number:
                phone_number = api_disbursement.mpesa_number
                disbursement_type = "B2C"
                
                if not phone_number or not amount:
                    logger.error(f"Missing phone number or amount for ApiDisbursement {api_disbursement_id}.")
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

            elif api_disbursement.b2b_account:
                paybill_number = api_disbursement.b2b_account.get("paybill_number")
                account_number = api_disbursement.b2b_account.get("account_number")
                disbursement_type = "B2B"
                
                if not paybill_number or not amount:
                    logger.error(f"Missing paybill number or amount for ApiDisbursement {api_disbursement_id}.")
                    return
            else:
                logger.error(f"No valid disbursement method found for ApiDisbursement {api_disbursement_id}.")
                return

            # Setup callback URLs
            result_url_b2c = f"{API_BASE_URL}/payment/mpesa/disburse_call_back/{tenant_id}/{api_disbursement_id}/result"
            timeout_url_b2c = f"{API_BASE_URL}/payment/mpesa/disburse_call_back/{tenant_id}/{api_disbursement_id}/timeout"

            result_url_b2b = f"{API_BASE_URL}/payment/mpesa/disburse_call_back_b2b/{tenant_id}/{api_disbursement_id}/result"
            timeout_url_b2b = f"{API_BASE_URL}/payment/mpesa/disburse_call_back_b2b/{tenant_id}/{api_disbursement_id}/timeout"

            # Get auth token
            auth_token = get_mpesa_auth_token()
            if not auth_token:
                logger.error("Failed to get M-Pesa authorization token.")
                return

            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
            
            # Build payload based on disbursement type
            if disbursement_type == "B2C":
                payload = {
                    "OriginatorConversationID": str(api_disbursement_id),
                    "InitiatorName": INITIATOR_NAME,
                    "SecurityCredential": SECURITY_CREDENTIAL,
                    "CommandID": "BusinessPayment",
                    "Amount": str(int(amount)),
                    "PartyA": MPESA_SHORTCODE,
                    "PartyB": formatted_number,
                    "Remarks": "Account withdraw",
                    "QueueTimeOutURL": timeout_url_b2c,
                    "ResultURL": result_url_b2c,
                    "Occasion": "Payment"
                }
                api_url = B2C_URL
                
            else:  # B2B
                payload = {
                    "Initiator": INITIATOR_NAME,
                    "SecurityCredential": SECURITY_CREDENTIAL,
                    "CommandID": "BusinessPayBill",
                    "SenderIdentifierType": "4",
                    "RecieverIdentifierType": "4",
                    "Amount": str(int(amount)),
                    "PartyA": MPESA_SHORTCODE,
                    "PartyB": paybill_number,
                    "AccountReference": account_number,
                    "Remarks": "Account withdraw",
                    "QueueTimeOutURL": timeout_url_b2b,
                    "ResultURL": result_url_b2b
                }
                api_url = B2B_URL

            # Make the request
            logger.info(f"Sending {disbursement_type} request with payload: {payload}")
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            try:
                response_data = response.json()
                logger.info(f"M-Pesa response: {response_data}")
                
                if response.status_code == 200 and response_data.get("ResponseCode") == "0":
                    api_disbursement.status = "initiated"
                    api_disbursement.mpesa_conversation_id = response_data.get("ConversationID")
                    api_disbursement.mpesa_originator_conversation_id = response_data.get("OriginatorConversationID")
                    db.session.commit()
                    logger.info(f"Disbursement {api_disbursement_id} successfully initiated")
                else:
                    error_msg = response_data.get("errorMessage") or response_data.get("ResponseDescription", "Unknown error")
                    logger.error(f"Failed to initiate disbursement {api_disbursement_id}: {error_msg}")
                    api_disbursement.status = "failed"
                    api_disbursement.error_message = error_msg
                    db.session.commit()
                    
            except ValueError as json_error:
                logger.error(f"Invalid JSON response: {response.text}")
                api_disbursement.status = "failed"
                api_disbursement.error_message = f"Invalid response from M-Pesa: {response.text}"
                db.session.commit()
                
    except requests.exceptions.RequestException as e:
        db.session.rollback()
        logger.exception(f"Network error initiating disbursement for {api_disbursement_id}: {e}")
        self.retry(exc=e, countdown=2 ** self.request.retries)
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error initiating disbursement for {api_disbursement_id}: {e}")
        self.retry(exc=e, countdown=2 ** self.request.retries)