"""
Salesforce REST API Client

A generic REST client for interacting with any Salesforce REST API endpoint.
Supports CRUD operations, queries, describe, and composite requests.

Usage:
    from sf_auth import SalesforceAuth
    from sf_rest_client import SalesforceRESTClient

    auth = SalesforceAuth(username=..., password=..., security_token=...)
    auth.authenticate_simple()

    client = SalesforceRESTClient(auth)
    
    # Query
    results = client.query("SELECT Id, Name FROM Account LIMIT 5")
    
    # Create
    record_id = client.create("Account", {"Name": "Acme Corp"})
    
    # Read
    account = client.read("Account", record_id)
    
    # Update
    client.update("Account", record_id, {"Industry": "Technology"})
    
    # Delete
    client.delete("Account", record_id)
"""

import json
import requests


API_VERSION = "v62.0"


class SalesforceRESTClient:
    """Generic Salesforce REST API client."""

    def __init__(self, auth):
        self.auth = auth
        self.base_url = f"{auth.instance_url}/services/data/{API_VERSION}"

    def _request(self, method, endpoint, data=None, params=None):
        """Make an authenticated request to the Salesforce REST API."""
        url = f"{self.base_url}{endpoint}"
        headers = self.auth.get_headers()

        response = requests.request(
            method=method, url=url, headers=headers, json=data, params=params,
        )

        if response.status_code in (200, 201):
            return response.json()
        elif response.status_code == 204:
            return None
        else:
            error_msg = response.text
            try:
                error_msg = json.dumps(response.json(), indent=2)
            except Exception:
                pass
            raise Exception(f"API Error ({response.status_code}): {error_msg}")

    # ── CRUD Operations ───────────────────────────────────────

    def create(self, sobject, data):
        """Create a new record."""
        result = self._request("POST", f"/sobjects/{sobject}/", data=data)
        if result and result.get("success"):
            print(f"✅ Created {sobject}: {result['id']}")
            return result["id"]
        else:
            raise Exception(f"Create failed: {result}")

    def read(self, sobject, record_id, fields=None):
        """Read a record by ID."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return self._request("GET", f"/sobjects/{sobject}/{record_id}", params=params)

    def update(self, sobject, record_id, data):
        """Update an existing record."""
        self._request("PATCH", f"/sobjects/{sobject}/{record_id}", data=data)
        print(f"✅ Updated {sobject}: {record_id}")

    def delete(self, sobject, record_id):
        """Delete a record."""
        self._request("DELETE", f"/sobjects/{sobject}/{record_id}")
        print(f"✅ Deleted {sobject}: {record_id}")

    def upsert(self, sobject, external_id_field, external_id_value, data):
        """Upsert a record using an external ID."""
        return self._request(
            "PATCH",
            f"/sobjects/{sobject}/{external_id_field}/{external_id_value}",
            data=data,
        )

    # ── Query ─────────────────────────────────────────────────

    def query(self, soql):
        """Execute a SOQL query."""
        result = self._request("GET", "/query/", params={"q": soql})
        records = result.get("records", [])
        print(f"📊 Query returned {result.get('totalSize', 0)} records")
        return records

    def query_all(self, soql):
        """Execute a SOQL query with auto-pagination."""
        result = self._request("GET", "/query/", params={"q": soql})
        all_records = result.get("records", [])

        while not result.get("done", True):
            next_url = result["nextRecordsUrl"]
            endpoint = next_url.replace(f"/services/data/{API_VERSION}", "")
            result = self._request("GET", endpoint)
            all_records.extend(result.get("records", []))

        print(f"📊 Query returned {len(all_records)} total records")
        return all_records

    def search(self, sosl):
        """Execute a SOSL search."""
        result = self._request("GET", "/search/", params={"q": sosl})
        return result.get("searchRecords", [])

    # ── Describe ──────────────────────────────────────────────

    def describe_global(self):
        """List all available objects."""
        result = self._request("GET", "/sobjects/")
        return result.get("sobjects", [])

    def describe_object(self, sobject):
        """Get full metadata for an object."""
        return self._request("GET", f"/sobjects/{sobject}/describe/")

    # ── Composite ─────────────────────────────────────────────

    def composite(self, requests_list, all_or_none=True):
        """Execute multiple operations in a single API call."""
        data = {
            "allOrNone": all_or_none,
            "compositeRequest": requests_list,
        }
        return self._request("POST", "/composite/", data=data)

    # ── Utility ───────────────────────────────────────────────

    def get_api_limits(self):
        """Get current API usage limits."""
        return self._request("GET", "/limits/")


if __name__ == "__main__":
    from sf_auth import SalesforceAuth

    auth = SalesforceAuth()
    auth.authenticate_simple()

    client = SalesforceRESTClient(auth)

    accounts = client.query("SELECT Id, Name, Industry FROM Account LIMIT 5")
    for acc in accounts:
        print(f"  {acc['Name']} — {acc.get('Industry', 'N/A')}")
