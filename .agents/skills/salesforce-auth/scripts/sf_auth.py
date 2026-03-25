"""
Salesforce OAuth 2.0 Authentication Helper

Handles authentication with Salesforce using the Username-Password flow.
Returns access_token and instance_url for subsequent API calls.

Usage:
    from sf_auth import SalesforceAuth
    
    auth = SalesforceAuth()
    token_data = auth.authenticate()
    print(token_data['access_token'])
    print(token_data['instance_url'])
"""

import os
import requests
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".env"))


class SalesforceAuth:
    """Handles Salesforce OAuth 2.0 authentication."""

    def __init__(
        self,
        username=None,
        password=None,
        security_token=None,
        client_id=None,
        client_secret=None,
        login_url=None,
    ):
        self.username = username or os.getenv("SF_USERNAME", "")
        self.password = password or os.getenv("SF_PASSWORD", "")
        self.security_token = security_token or os.getenv("SF_SECURITY_TOKEN", "")
        self.client_id = client_id or os.getenv("SF_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("SF_CLIENT_SECRET", "")
        self.login_url = login_url or os.getenv(
            "SF_LOGIN_URL", "https://login.salesforce.com"
        )

        self.access_token = None
        self.instance_url = None

    def authenticate(self):
        """Authenticate using the Username-Password OAuth 2.0 flow."""
        token_url = f"{self.login_url}/services/oauth2/token"

        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": f"{self.password}{self.security_token}",
        }

        response = requests.post(token_url, data=payload)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.instance_url = data["instance_url"]
            print(f"✅ Authenticated successfully!")
            print(f"   Instance URL: {self.instance_url}")
            return data
        else:
            error = response.json()
            raise Exception(
                f"❌ Authentication failed: {error.get('error_description', error)}"
            )

    def authenticate_simple(self):
        """Simplified authentication using only username, password, and security token.
        This works without a Connected App by using SOAP login."""
        soap_url = f"{self.login_url}/services/Soap/u/62.0"

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:urn="urn:partner.soap.sforce.com">
  <soapenv:Body>
    <urn:login>
      <urn:username>{self.username}</urn:username>
      <urn:password>{self.password}{self.security_token}</urn:password>
    </urn:login>
  </soapenv:Body>
</soapenv:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "login",
        }

        response = requests.post(soap_url, data=soap_body, headers=headers)

        if response.status_code == 200:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(response.text)
            ns = {
                "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
                "sf": "urn:partner.soap.sforce.com",
            }

            session_id = root.find(".//sf:sessionId", ns).text
            server_url = root.find(".//sf:serverUrl", ns).text

            from urllib.parse import urlparse

            parsed = urlparse(server_url)
            instance_url = f"{parsed.scheme}://{parsed.hostname}"

            self.access_token = session_id
            self.instance_url = instance_url

            print(f"✅ Authenticated successfully (SOAP login)!")
            print(f"   Instance URL: {self.instance_url}")

            return {
                "access_token": session_id,
                "instance_url": instance_url,
            }
        else:
            raise Exception(f"❌ SOAP login failed: {response.text}")

    def get_headers(self):
        """Get authorization headers for API calls."""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def revoke_token(self):
        """Revoke the current access token."""
        if self.access_token:
            revoke_url = f"{self.login_url}/services/oauth2/revoke"
            requests.post(revoke_url, data={"token": self.access_token})
            self.access_token = None
            self.instance_url = None
            print("🔒 Token revoked successfully.")


if __name__ == "__main__":
    auth = SalesforceAuth()
    result = auth.authenticate_simple()
    print(f"\nAccess Token: {result['access_token'][:50]}...")
    print(f"Instance URL: {result['instance_url']}")
