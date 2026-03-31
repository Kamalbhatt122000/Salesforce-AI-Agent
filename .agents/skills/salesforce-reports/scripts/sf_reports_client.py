"""
Salesforce Reports Client (Analytics API)
══════════════════════════════════════════
Wraps the Salesforce Analytics REST API for listing, describing,
and running native Salesforce reports (Tabular, Summary, Matrix).

Usage:
    from sf_auth import SalesforceAuth
    from sf_reports_client import SalesforceReportsClient

    auth = SalesforceAuth(username=..., password=..., security_token=...)
    auth.authenticate_simple()

    client = SalesforceReportsClient(auth)

    # List all reports
    reports = client.list_reports()

    # Run a report
    result = client.run_report("00O5g000004XXXXX")

    # Run with runtime filters
    result = client.run_report("00O5g000004XXXXX", filters=[
        {"column": "STAGE_NAME", "operator": "equals", "value": "Prospecting"}
    ])
"""

import json
import requests

API_VERSION = "v62.0"


class SalesforceReportsClient:
    """Salesforce Analytics API client for native report operations."""

    def __init__(self, auth):
        """
        Initialize with an authenticated SalesforceAuth instance.

        Args:
            auth: SalesforceAuth instance (must be authenticated)
        """
        self.auth = auth
        self.base_url = f"{auth.instance_url}/services/data/{API_VERSION}"
        self.analytics_url = f"{self.base_url}/analytics"

    def _request(self, method, url, data=None, params=None):
        """Make an authenticated request to the Analytics API."""
        headers = self.auth.get_headers()
        response = requests.request(
            method=method, url=url, headers=headers, json=data, params=params
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
            raise Exception(f"Analytics API Error ({response.status_code}): {error_msg}")

    # ── Folders ───────────────────────────────────────────────

    def list_folders(self):
        """
        List all report folders the current user can access.

        Returns:
            dict: {
                "folders": [...],
                "categorized": {"public": [...], "private": [...], "shared": [...]},
                "count": int
            }
        """
        soql = (
            "SELECT Id, Name, Type, DeveloperName, AccessType, CreatedBy.Name, "
            "LastModifiedDate FROM Folder "
            "WHERE Type = 'Report' AND DeveloperName != '' "
            "ORDER BY Name ASC"
        )
        url = f"{self.base_url}/query/"
        result = self._request("GET", url, params={"q": soql})
        raw = result.get("records", [])

        folders = []
        for r in raw:
            created_by = r.get("CreatedBy") or {}
            folders.append({
                "id": r.get("Id"),
                "name": r.get("Name", "Untitled"),
                "developerName": r.get("DeveloperName", ""),
                "accessType": r.get("AccessType", "Public"),
                "createdBy": created_by.get("Name", "—") if isinstance(created_by, dict) else "—",
                "lastModified": r.get("LastModifiedDate", ""),
            })

        categorized = {"public": [], "private": [], "shared": []}
        for f in folders:
            access = (f.get("accessType") or "").lower()
            if "public" in access:
                categorized["public"].append(f)
            elif "hidden" in access:
                categorized["private"].append(f)
            else:
                categorized["shared"].append(f)

        print(f"📁 Found {len(folders)} report folders")
        return {
            "folders": folders,
            "categorized": categorized,
            "count": len(folders),
            "message": f"Found {len(folders)} report folders.",
        }

    # ── Reports List ──────────────────────────────────────────

    def list_reports(self, folder_id=None, search_term=None, limit=50):
        """
        List reports, optionally filtered by folder or search term.

        Args:
            folder_id: Optional Salesforce folder ID to filter by
            search_term: Optional partial name to search for
            limit: Max reports to return (default 50)

        Returns:
            dict: { "reports": [...], "count": int }
        """
        soql = (
            "SELECT Id, Name, DeveloperName, Description, FolderName, Format, "
            "LastRunDate, CreatedBy.Name, LastModifiedDate, LastModifiedBy.Name "
            "FROM Report "
        )
        conditions = []
        if folder_id:
            conditions.append(f"OwnerId = '{folder_id}'")
        if search_term:
            safe = search_term.replace("'", "\\'")
            conditions.append(f"Name LIKE '%{safe}%'")

        if conditions:
            soql += "WHERE " + " AND ".join(conditions) + " "
        soql += f"ORDER BY LastRunDate DESC NULLS LAST LIMIT {limit}"

        url = f"{self.base_url}/query/"
        result = self._request("GET", url, params={"q": soql})
        raw = result.get("records", [])

        format_labels = {
            "TABULAR": "Tabular",
            "SUMMARY": "Summary",
            "MATRIX": "Matrix",
            "MULTI_BLOCK": "Joined",
        }

        reports = []
        for r in raw:
            created_by = r.get("CreatedBy") or {}
            last_mod_by = r.get("LastModifiedBy") or {}
            fmt = r.get("Format", "TABULAR")
            reports.append({
                "id": r.get("Id"),
                "name": r.get("Name", "Untitled"),
                "developerName": r.get("DeveloperName", ""),
                "description": r.get("Description") or "",
                "folderName": r.get("FolderName", "—"),
                "format": fmt,
                "formatLabel": format_labels.get(fmt, fmt),
                "lastRunDate": r.get("LastRunDate") or "Never",
                "createdBy": created_by.get("Name", "—") if isinstance(created_by, dict) else "—",
                "lastModifiedDate": r.get("LastModifiedDate", ""),
                "lastModifiedBy": last_mod_by.get("Name", "—") if isinstance(last_mod_by, dict) else "—",
            })

        print(f"📋 Found {len(reports)} reports")
        return {
            "reports": reports,
            "count": len(reports),
            "folder_id": folder_id,
            "message": f"Found {len(reports)} reports.",
        }

    # ── Report Metadata ───────────────────────────────────────

    def get_metadata(self, report_id):
        """
        Get report structure: columns, groupings, and existing filters.

        Args:
            report_id: Salesforce Report ID (15 or 18 chars, starts with 00O)

        Returns:
            dict: { "columns": [...], "groupings": [...], "filters": [...], ... }
        """
        url = f"{self.analytics_url}/reports/{report_id}/describe"
        result = self._request("GET", url)

        metadata = result.get("reportMetadata", {})
        extended = result.get("reportExtendedMetadata", {})

        # Columns
        columns = []
        for col in metadata.get("detailColumns", []):
            info = extended.get("detailColumnInfo", {}).get(col, {})
            columns.append({
                "apiName": col,
                "label": info.get("label", col),
                "dataType": info.get("dataType", "string"),
            })

        # Groupings
        groupings = []
        for g in metadata.get("groupingsDown", []):
            groupings.append({
                "name": g.get("name", ""),
                "sortOrder": g.get("sortOrder", "Asc"),
                "dateGranularity": g.get("dateGranularity", "NONE"),
            })

        # Existing filters
        filters = []
        for f in metadata.get("reportFilters", []):
            filters.append({
                "column": f.get("column", ""),
                "operator": f.get("operator", "equals"),
                "value": f.get("value", ""),
            })

        print(f"📊 Report '{metadata.get('name', '')}': {len(columns)} columns, {len(groupings)} groupings")
        return {
            "reportId": report_id,
            "name": metadata.get("name", ""),
            "reportFormat": metadata.get("reportFormat", "TABULAR"),
            "reportType": metadata.get("reportType", {}).get("label", ""),
            "columns": columns,
            "groupings": groupings,
            "filters": filters,
            "message": (
                f"Report '{metadata.get('name', '')}' has {len(columns)} columns, "
                f"{len(groupings)} groupings, {len(filters)} existing filters."
            ),
        }

    # ── Run Report ────────────────────────────────────────────

    def run_report(self, report_id, filters=None, limit_rows=2000):
        """
        Execute a Salesforce report and return formatted results.

        Args:
            report_id: Salesforce Report ID
            filters: Optional list of runtime filter dicts:
                     [{"column": "STAGE_NAME", "operator": "equals", "value": "Prospecting"}]
            limit_rows: Max rows to return (default 2000, API cap)

        Returns:
            dict: {
                "reportId": str,
                "name": str,
                "reportFormat": str,
                "columns": [...],
                "rows": [...],
                "totalRows": int,
                "rowsReturned": int,
                "aggregates": {...},
                "groupings": [...],
                "filters": [...],
                "reportUrl": str,
                "message": str
            }
        """
        body = {}
        if filters:
            body["reportMetadata"] = {
                "reportFilters": [
                    {"column": f["column"], "operator": f["operator"], "value": f["value"]}
                    for f in filters
                ]
            }

        url = f"{self.analytics_url}/reports/{report_id}"
        print(f"▶️  Running report {report_id}...")
        result = self._request("POST", url, data=body if body else None)

        metadata = result.get("reportMetadata", {})
        extended = result.get("reportExtendedMetadata", {})
        fact_map = result.get("factMap", {})
        report_format = metadata.get("reportFormat", "TABULAR")

        # Build column list
        detail_columns = metadata.get("detailColumns", [])
        column_info = extended.get("detailColumnInfo", {})
        columns = []
        for col in detail_columns:
            info = column_info.get(col, {})
            columns.append({
                "apiName": col,
                "label": info.get("label", col),
                "dataType": info.get("dataType", "string"),
            })

        rows = []
        aggregates = {}

        if report_format == "TABULAR":
            rows, aggregates = self._parse_tabular(fact_map, columns)

        elif report_format == "SUMMARY":
            rows, aggregates = self._parse_summary(
                fact_map, columns, result.get("groupingsDown", {}).get("groupings", [])
            )

        elif report_format == "MATRIX":
            rows, aggregates = self._parse_matrix(fact_map, columns)

        # Cap rows
        total_rows = len(rows)
        if total_rows > limit_rows:
            rows = rows[:limit_rows]

        # Grouping labels for frontend
        groupings = []
        for g in metadata.get("groupingsDown", []):
            g_info = extended.get("groupColumnInfo", {}).get(g.get("name", ""), {})
            groupings.append({
                "name": g.get("name", ""),
                "label": g_info.get("label", g.get("name", "")),
                "sortOrder": g.get("sortOrder", "Asc"),
            })

        report_name = metadata.get("name", "")
        print(f"✅ Report '{report_name}' returned {len(rows)} rows (total: {total_rows})")

        return {
            "reportId": report_id,
            "name": report_name,
            "reportFormat": report_format,
            "columns": columns,
            "rows": rows,
            "totalRows": total_rows,
            "rowsReturned": len(rows),
            "aggregates": aggregates,
            "groupings": groupings,
            "filters": metadata.get("reportFilters", []),
            "reportUrl": f"{self.auth.instance_url}/{report_id}",
            "message": f"Report '{report_name}' returned {len(rows)} rows.",
        }

    # ── factMap Parsers ───────────────────────────────────────

    def _parse_tabular(self, fact_map, columns):
        """Parse a TABULAR report factMap."""
        rows = []
        aggregates = {}
        t_data = fact_map.get("T!T", {})

        for row_data in t_data.get("rows", []):
            row = {}
            for i, cell in enumerate(row_data.get("dataCells", [])):
                if i < len(columns):
                    row[columns[i]["label"]] = cell.get("label", cell.get("value", ""))
            rows.append(row)

        for agg in t_data.get("aggregates", []):
            label = agg.get("label", "")
            if label:
                aggregates[label] = agg.get("value", 0)

        return rows, aggregates

    def _parse_summary(self, fact_map, columns, groupings):
        """Parse a SUMMARY report factMap."""
        rows = []
        aggregates = {}

        for group in groupings:
            group_key = group.get("key", "")
            group_label = group.get("label", "Unknown")
            fact_key = f"{group_key}!T"
            g_data = fact_map.get(fact_key, {})

            for row_data in g_data.get("rows", []):
                row = {"_group": group_label}
                for i, cell in enumerate(row_data.get("dataCells", [])):
                    if i < len(columns):
                        row[columns[i]["label"]] = cell.get("label", cell.get("value", ""))
                rows.append(row)

            # Group-level subtotals
            for agg in g_data.get("aggregates", []):
                agg_label = agg.get("label", "")
                if agg_label:
                    if "_group_aggregates" not in aggregates:
                        aggregates["_group_aggregates"] = []
                    aggregates["_group_aggregates"].append({
                        "group": group_label,
                        "label": agg_label,
                        "value": agg.get("value", 0),
                    })

        # Grand total
        for agg in fact_map.get("T!T", {}).get("aggregates", []):
            label = agg.get("label", "")
            if label:
                aggregates[label] = agg.get("value", 0)

        return rows, aggregates

    def _parse_matrix(self, fact_map, columns):
        """Parse a MATRIX report factMap (grand totals + available rows)."""
        rows = []
        aggregates = {}

        # Grand totals
        for agg in fact_map.get("T!T", {}).get("aggregates", []):
            label = agg.get("label", "")
            if label:
                aggregates[label] = agg.get("value", 0)

        # Row data from non-grand-total keys
        for key, data in fact_map.items():
            if key == "T!T":
                continue
            for row_data in data.get("rows", []):
                row = {"_factKey": key}
                for i, cell in enumerate(row_data.get("dataCells", [])):
                    if i < len(columns):
                        row[columns[i]["label"]] = cell.get("label", cell.get("value", ""))
                if len(row) > 1:
                    rows.append(row)

        return rows, aggregates


# ── Quick Usage ──────────────────────────────────────────────
if __name__ == "__main__":
    from sf_auth import SalesforceAuth

    auth = SalesforceAuth()
    auth.authenticate_simple()

    client = SalesforceReportsClient(auth)

    # List all reports
    result = client.list_reports()
    print(f"\nFirst 5 reports:")
    for r in result["reports"][:5]:
        print(f"  [{r['formatLabel']}] {r['name']} — {r['folderName']} (last run: {r['lastRunDate']})")

    # Run the first report
    if result["reports"]:
        first_id = result["reports"][0]["id"]
        run_result = client.run_report(first_id)
        print(f"\nReport '{run_result['name']}': {run_result['rowsReturned']} rows")
        if run_result["rows"]:
            print("First row:", run_result["rows"][0])
