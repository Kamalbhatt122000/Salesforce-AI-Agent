"""
Salesforce SOQL/SOSL Query Executor

Executes SOQL and SOSL queries with automatic pagination.
Provides convenience methods for common query patterns.

Usage:
    from sf_auth import SalesforceAuth
    from sf_query import SalesforceQuery

    auth = SalesforceAuth(username=..., password=..., security_token=...)
    auth.authenticate_simple()

    q = SalesforceQuery(auth)

    # Simple query
    accounts = q.soql("SELECT Id, Name FROM Account LIMIT 10")

    # Query with auto-pagination (all results)
    all_contacts = q.soql_all("SELECT Id, Name FROM Contact")

    # Search
    results = q.sosl("FIND {Acme} IN ALL FIELDS RETURNING Account(Name, Id)")

    # Convenience methods
    account = q.find_by_id("Account", "001xxx")
    accounts = q.find_by_field("Account", "Industry", "Technology")
    count = q.count("Account", "Industry = 'Technology'")
"""

import requests


API_VERSION = "v62.0"


class SalesforceQuery:
    """SOQL and SOSL query executor with pagination support."""

    def __init__(self, auth):
        self.auth = auth
        self.base_url = f"{auth.instance_url}/services/data/{API_VERSION}"

    def _get(self, url, params=None):
        """Make an authenticated GET request."""
        headers = self.auth.get_headers()
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Query failed ({response.status_code}): {response.text}")

    # ── SOQL ──────────────────────────────────────────────────

    def soql(self, query):
        """Execute a SOQL query. Returns first page of results."""
        result = self._get(f"{self.base_url}/query/", params={"q": query})
        records = result.get("records", [])
        total = result.get("totalSize", 0)
        done = result.get("done", True)

        print(f"📊 SOQL returned {len(records)} of {total} records{'' if done else ' (more available)'}")
        return records

    def soql_all(self, query):
        """Execute SOQL with auto-pagination. Fetches ALL matching records."""
        result = self._get(f"{self.base_url}/query/", params={"q": query})
        all_records = result.get("records", [])
        total = result.get("totalSize", 0)

        page = 1
        while not result.get("done", True):
            next_url = f"{self.auth.instance_url}{result['nextRecordsUrl']}"
            result = self._get(next_url)
            all_records.extend(result.get("records", []))
            page += 1

        print(f"📊 SOQL returned {len(all_records)} of {total} records ({page} page(s))")
        return all_records

    def soql_first(self, query):
        """Execute SOQL and return only the first record."""
        records = self.soql(query)
        return records[0] if records else None

    # ── SOSL ──────────────────────────────────────────────────

    def sosl(self, search_query):
        """Execute a SOSL search."""
        result = self._get(f"{self.base_url}/search/", params={"q": search_query})
        records = result.get("searchRecords", [])
        print(f"🔍 SOSL returned {len(records)} results")
        return records

    # ── Convenience Methods ───────────────────────────────────

    def find_by_id(self, sobject, record_id, fields=None):
        """Find a record by its ID."""
        if fields:
            field_str = ", ".join(fields)
        else:
            field_str = "Id, Name"

        query = f"SELECT {field_str} FROM {sobject} WHERE Id = '{record_id}'"
        return self.soql_first(query)

    def find_by_field(self, sobject, field_name, field_value, select_fields=None, limit=100):
        """Find records by a field value."""
        fields = ", ".join(select_fields) if select_fields else "Id, Name"
        query = f"SELECT {fields} FROM {sobject} WHERE {field_name} = '{field_value}' LIMIT {limit}"
        return self.soql(query)

    def count(self, sobject, where_clause=None):
        """Count records in an object."""
        query = f"SELECT COUNT() FROM {sobject}"
        if where_clause:
            query += f" WHERE {where_clause}"

        result = self._get(f"{self.base_url}/query/", params={"q": query})
        count = result.get("totalSize", 0)
        print(f"📊 Count: {count} {sobject} records")
        return count

    def describe_fields(self, sobject):
        """Get all field names and types for an object."""
        result = self._get(f"{self.base_url}/sobjects/{sobject}/describe/")
        fields = [
            {"name": f["name"], "type": f["type"], "label": f["label"]}
            for f in result.get("fields", [])
        ]
        print(f"📋 {sobject} has {len(fields)} fields")
        return fields

    def list_objects(self):
        """List all available objects in the org."""
        result = self._get(f"{self.base_url}/sobjects/")
        objects = [obj["name"] for obj in result.get("sobjects", [])]
        print(f"📋 Org has {len(objects)} objects")
        return objects


if __name__ == "__main__":
    from sf_auth import SalesforceAuth

    auth = SalesforceAuth()
    auth.authenticate_simple()

    q = SalesforceQuery(auth)

    objects = q.list_objects()
    print(f"\nFirst 10 objects: {objects[:10]}")

    q.count("Account")

    accounts = q.soql("SELECT Id, Name, Industry FROM Account LIMIT 5")
    for acc in accounts:
        print(f"  {acc['Name']} — {acc.get('Industry', 'N/A')}")
