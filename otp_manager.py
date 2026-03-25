"""
OTP Manager — Salesforce Email-Based OTP Verification
══════════════════════════════════════════════════════
Generates, sends (via Salesforce SingleEmailMessage REST API),
and verifies one-time passwords for sensitive operations.
"""

import random
import string
import time
import requests
import json


# OTP validity window in seconds (5 minutes)
OTP_EXPIRY_SECONDS = 300

# In-memory OTP store: { session_key: { "otp": str, "expires": float, "attempts": int } }
_otp_store = {}


def generate_otp(length=6):
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def send_otp_via_salesforce(auth, recipient_email, otp_code, operation_summary=""):
    """
    Send an OTP email using the Salesforce REST API (SingleEmailMessage).

    Args:
        auth: Authenticated SalesforceAuth instance (has instance_url, access_token).
        recipient_email: Email address to send OTP to.
        otp_code: The OTP code string.
        operation_summary: Human-readable description of the operation being verified.

    Returns:
        dict: { "success": True } or { "error": "..." }
    """
    url = f"{auth.instance_url}/services/data/v62.0/actions/standard/emailSimple"

    headers = auth.get_headers()

    email_body = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   SALESFORCE AI AGENT\n"
        f"   Security Verification Code\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"A sensitive operation was requested on\n"
        f"your Salesforce org:\n"
        f"\n"
        f"  >> {operation_summary or 'Update / Delete operation'}\n"
        f"\n"
        f"Your one-time verification code is:\n"
        f"\n"
        f"        {otp_code}\n"
        f"\n"
        f"This code expires in 5 minutes.\n"
        f"If you did not request this, please\n"
        f"ignore this email.\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Salesforce AI Agent — Security Verification\n"
    )

    payload = {
        "inputs": [
            {
                "emailSubject": "Salesforce AI Agent — Security Verification Required",
                "emailBody": email_body,
                "emailAddresses": recipient_email,
                "senderType": "CurrentUser",
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in (200, 201):
            result = response.json()
            # Salesforce returns a list; check first item
            if isinstance(result, list) and len(result) > 0:
                item = result[0]
                if item.get("isSuccess"):
                    print(f"  [OTP] Email sent to {recipient_email}")
                    return {"success": True}
                else:
                    errors = item.get("errors", [])
                    err_msg = "; ".join(str(e) for e in errors) if errors else "Unknown error"
                    print(f"  [OTP ERROR] {err_msg}")
                    return {"error": f"Failed to send OTP email: {err_msg}"}
            return {"success": True}
        else:
            error_text = response.text
            try:
                error_text = json.dumps(response.json(), indent=2)
            except Exception:
                pass
            print(f"  [OTP ERROR] HTTP {response.status_code}: {error_text}")
            return {"error": f"Salesforce email API error ({response.status_code}): {error_text}"}
    except Exception as e:
        print(f"  [OTP ERROR] {e}")
        return {"error": str(e)}


def create_and_send_otp(auth, recipient_email, session_key, operation_summary=""):
    """
    Generate an OTP, store it, and send it via Salesforce email.

    Args:
        auth: Authenticated SalesforceAuth instance.
        recipient_email: Where to send the OTP.
        session_key: Unique key to identify this OTP session (e.g. "update_Lead_00Qxxx").
        operation_summary: Description of the operation.

    Returns:
        dict: { "success": True, "message": "..." } or { "error": "..." }
    """
    otp_code = generate_otp()

    # Store OTP with expiry
    _otp_store[session_key] = {
        "otp": otp_code,
        "expires": time.time() + OTP_EXPIRY_SECONDS,
        "attempts": 0,
    }

    print(f"  [OTP] Generated OTP for session '{session_key}': {otp_code}")

    # Send via Salesforce
    send_result = send_otp_via_salesforce(auth, recipient_email, otp_code, operation_summary)

    if "error" in send_result:
        # Clean up on failure
        _otp_store.pop(session_key, None)
        return send_result

    return {
        "success": True,
        "message": f"A verification code has been sent to {recipient_email}. Please enter the code to proceed.",
        "session_key": session_key,
    }


def verify_otp(session_key, user_otp):
    """
    Verify an OTP for a given session key.

    Args:
        session_key: The session key used when creating the OTP.
        user_otp: The OTP code provided by the user.

    Returns:
        dict: { "verified": True } or { "verified": False, "error": "..." }
    """
    entry = _otp_store.get(session_key)

    if not entry:
        return {"verified": False, "error": "No OTP found for this session. Please request a new code."}

    # Check expiry
    if time.time() > entry["expires"]:
        _otp_store.pop(session_key, None)
        return {"verified": False, "error": "OTP has expired. Please request a new verification code."}

    # Check max attempts (max 3)
    if entry["attempts"] >= 3:
        _otp_store.pop(session_key, None)
        return {"verified": False, "error": "Too many failed attempts. Please request a new verification code."}

    # Increment attempts
    entry["attempts"] += 1

    # Verify
    if str(user_otp).strip() == str(entry["otp"]).strip():
        _otp_store.pop(session_key, None)
        print(f"  [OTP] Verified successfully for session '{session_key}'")
        return {"verified": True}
    else:
        remaining = 3 - entry["attempts"]
        print(f"  [OTP] Verification failed for session '{session_key}' (attempt {entry['attempts']}/3)")
        return {
            "verified": False,
            "error": f"Incorrect verification code. {remaining} attempt(s) remaining."
        }


def cleanup_expired():
    """Remove expired OTP entries from the store."""
    now = time.time()
    expired_keys = [k for k, v in _otp_store.items() if now > v["expires"]]
    for k in expired_keys:
        _otp_store.pop(k, None)
