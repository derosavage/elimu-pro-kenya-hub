"""Safaricom Daraja service layer.

IMPLEMENTED BUT NOT LIVE-TESTED: no Daraja credentials/sandbox were available
when this was written. It reads all credentials from environment variables and
reports `configured() == False` until they are set. The STK callback handler is
not implemented yet (see docs/DEPLOYMENT.md).
"""
import base64
import json
import os
import urllib.request
from datetime import datetime


class MpesaNotConfigured(Exception):
    pass


REQUIRED = ("MPESA_CONSUMER_KEY", "MPESA_CONSUMER_SECRET", "MPESA_SHORTCODE", "MPESA_PASSKEY", "MPESA_CALLBACK_URL")


def configured():
    return all(os.environ.get(k) for k in REQUIRED)


def _base():
    return "https://api.safaricom.co.ke" if os.environ.get("MPESA_ENV") == "production" else "https://sandbox.safaricom.co.ke"


def _token():
    creds = f"{os.environ['MPESA_CONSUMER_KEY']}:{os.environ['MPESA_CONSUMER_SECRET']}".encode()
    req = urllib.request.Request(f"{_base()}/oauth/v1/generate?grant_type=client_credentials",
                                 headers={"Authorization": "Basic " + base64.b64encode(creds).decode()})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["access_token"]


def stk_push(phone, amount, account_ref, description="School fees"):
    if not configured():
        raise MpesaNotConfigured("M-Pesa is not configured on this server")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    shortcode = os.environ["MPESA_SHORTCODE"]
    password = base64.b64encode(f"{shortcode}{os.environ['MPESA_PASSKEY']}{ts}".encode()).decode()
    body = json.dumps({
        "BusinessShortCode": shortcode, "Password": password, "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline", "Amount": int(amount),
        "PartyA": phone.lstrip("+"), "PartyB": shortcode, "PhoneNumber": phone.lstrip("+"),
        "CallBackURL": os.environ["MPESA_CALLBACK_URL"], "AccountReference": account_ref[:12],
        "TransactionDesc": description[:13]}).encode()
    req = urllib.request.Request(f"{_base()}/mpesa/stkpush/v1/processrequest", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)
