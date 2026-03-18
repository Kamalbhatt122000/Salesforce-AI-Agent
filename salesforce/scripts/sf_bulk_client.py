"""
Salesforce Bulk API 2.0 Client

Manages bulk data operations: create job → upload CSV → close → poll → get results.
Designed for processing 2,000+ records efficiently.

Usage:
    from sf_auth import SalesforceAuth
    from sf_bulk_client import SalesforceBulkClient

    auth = SalesforceAuth(username=..., password=..., security_token=...)
    auth.authenticate_simple()

    bulk = SalesforceBulkClient(auth)

    # Insert records from CSV
    job_id = bulk.insert_csv("Account", "Name,Industry\\nAcme,Technology\\nBeta,Finance")
    bulk.wait_for_completion(job_id)
    results = bulk.get_results(job_id)
"""

import time
import requests


API_VERSION = "v62.0"


class SalesforceBulkClient:
    """Salesforce Bulk API 2.0 client for large data operations."""

    def __init__(self, auth):
        """
        Initialize with an authenticated SalesforceAuth instance.

        Args:
            auth: SalesforceAuth instance (must be authenticated)
        """
        self.auth = auth
        self.base_url = f"{auth.instance_url}/services/data/{API_VERSION}/jobs"

    def _headers_json(self):
        return {
            "Authorization": f"Bearer {self.auth.access_token}",
            "Content-Type": "application/json",
        }

    def _headers_csv(self):
        return {
            "Authorization": f"Bearer {self.auth.access_token}",
            "Content-Type": "text/csv",
        }

    # ── Job Management ────────────────────────────────────────

    def create_job(self, sobject, operation, external_id_field=None):
        """
        Create a bulk ingest job.

        Args:
            sobject: Object API name (e.g., 'Account')
            operation: 'insert', 'update', 'upsert', 'delete', 'hardDelete'
            external_id_field: Required for 'upsert' operation

        Returns:
            str: Job ID
        """
        payload = {
            "object": sobject,
            "operation": operation,
            "contentType": "CSV",
            "lineEnding": "CRLF",
        }

        if operation == "upsert" and external_id_field:
            payload["externalIdFieldName"] = external_id_field

        response = requests.post(
            f"{self.base_url}/ingest/",
            headers=self._headers_json(),
            json=payload,
        )

        if response.status_code in (200, 201):
            job = response.json()
            print(f"✅ Job created: {job['id']} ({operation} on {sobject})")
            return job["id"]
        else:
            raise Exception(f"Failed to create job: {response.text}")

    def upload_csv(self, job_id, csv_data):
        """
        Upload CSV data to a job.

        Args:
            job_id: Bulk job ID
            csv_data: CSV string data (with header row)
        """
        response = requests.put(
            f"{self.base_url}/ingest/{job_id}/batches/",
            headers=self._headers_csv(),
            data=csv_data.encode("utf-8"),
        )

        if response.status_code in (200, 201):
            print(f"✅ CSV data uploaded to job {job_id}")
        else:
            raise Exception(f"Failed to upload CSV: {response.text}")

    def close_job(self, job_id):
        """Close a job to start processing."""
        response = requests.patch(
            f"{self.base_url}/ingest/{job_id}",
            headers=self._headers_json(),
            json={"state": "UploadComplete"},
        )

        if response.status_code in (200, 201):
            print(f"✅ Job {job_id} closed — processing started")
        else:
            raise Exception(f"Failed to close job: {response.text}")

    def abort_job(self, job_id):
        """Abort a running job."""
        response = requests.patch(
            f"{self.base_url}/ingest/{job_id}",
            headers=self._headers_json(),
            json={"state": "Aborted"},
        )

        if response.status_code in (200, 201):
            print(f"⛔ Job {job_id} aborted")
        else:
            raise Exception(f"Failed to abort job: {response.text}")

    def get_job_status(self, job_id):
        """
        Get the current status of a job.

        Returns:
            dict: Job info including state, numberRecordsProcessed, etc.
        """
        response = requests.get(
            f"{self.base_url}/ingest/{job_id}",
            headers=self._headers_json(),
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get job status: {response.text}")

    def wait_for_completion(self, job_id, poll_interval=15, max_wait=600):
        """
        Poll job status until completion.

        Args:
            job_id: Bulk job ID
            poll_interval: Seconds between polls (default: 15)
            max_wait: Maximum wait time in seconds (default: 600)

        Returns:
            dict: Final job status
        """
        elapsed = 0
        while elapsed < max_wait:
            status = self.get_job_status(job_id)
            state = status.get("state", "Unknown")
            processed = status.get("numberRecordsProcessed", 0)
            failed = status.get("numberRecordsFailed", 0)

            print(
                f"   ⏳ Job {job_id}: {state} "
                f"(processed: {processed}, failed: {failed})"
            )

            if state in ("JobComplete", "Failed", "Aborted"):
                if state == "JobComplete":
                    print(f"✅ Job completed! {processed} records processed, {failed} failed")
                elif state == "Failed":
                    print(f"❌ Job failed!")
                return status

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise Exception(f"Job {job_id} timed out after {max_wait} seconds")

    # ── Results ───────────────────────────────────────────────

    def get_successful_results(self, job_id):
        """Get CSV of successfully processed records."""
        response = requests.get(
            f"{self.base_url}/ingest/{job_id}/successfulResults/",
            headers={
                "Authorization": f"Bearer {self.auth.access_token}",
                "Accept": "text/csv",
            },
        )
        return response.text

    def get_failed_results(self, job_id):
        """Get CSV of failed records with error messages."""
        response = requests.get(
            f"{self.base_url}/ingest/{job_id}/failedResults/",
            headers={
                "Authorization": f"Bearer {self.auth.access_token}",
                "Accept": "text/csv",
            },
        )
        return response.text

    def get_unprocessed_records(self, job_id):
        """Get CSV of unprocessed records."""
        response = requests.get(
            f"{self.base_url}/ingest/{job_id}/unprocessedrecords/",
            headers={
                "Authorization": f"Bearer {self.auth.access_token}",
                "Accept": "text/csv",
            },
        )
        return response.text

    def get_results(self, job_id):
        """
        Get all results (successful, failed, unprocessed).

        Returns:
            dict: {'successful': str, 'failed': str, 'unprocessed': str}
        """
        return {
            "successful": self.get_successful_results(job_id),
            "failed": self.get_failed_results(job_id),
            "unprocessed": self.get_unprocessed_records(job_id),
        }

    # ── Convenience Methods ───────────────────────────────────

    def insert_csv(self, sobject, csv_data):
        """
        One-step insert: create job, upload CSV, close job.

        Args:
            sobject: Object API name
            csv_data: CSV string with header row

        Returns:
            str: Job ID (use wait_for_completion to wait)
        """
        job_id = self.create_job(sobject, "insert")
        self.upload_csv(job_id, csv_data)
        self.close_job(job_id)
        return job_id

    def update_csv(self, sobject, csv_data):
        """One-step update. CSV must include 'Id' column."""
        job_id = self.create_job(sobject, "update")
        self.upload_csv(job_id, csv_data)
        self.close_job(job_id)
        return job_id

    def delete_csv(self, sobject, csv_data):
        """One-step delete. CSV must have 'Id' column only."""
        job_id = self.create_job(sobject, "delete")
        self.upload_csv(job_id, csv_data)
        self.close_job(job_id)
        return job_id

    # ── Bulk Query ────────────────────────────────────────────

    def create_query_job(self, soql, operation="query"):
        """
        Create a bulk query job.

        Args:
            soql: SOQL query string
            operation: 'query' or 'queryAll' (includes deleted records)

        Returns:
            str: Query job ID
        """
        payload = {
            "operation": operation,
            "query": soql,
        }

        response = requests.post(
            f"{self.base_url}/query/",
            headers=self._headers_json(),
            json=payload,
        )

        if response.status_code in (200, 201):
            job = response.json()
            print(f"✅ Query job created: {job['id']}")
            return job["id"]
        else:
            raise Exception(f"Failed to create query job: {response.text}")

    def get_query_results(self, job_id):
        """
        Get bulk query results as CSV.

        Returns:
            str: CSV data
        """
        response = requests.get(
            f"{self.base_url}/query/{job_id}/results",
            headers={
                "Authorization": f"Bearer {self.auth.access_token}",
                "Accept": "text/csv",
            },
        )
        return response.text


# ── Quick Usage ──────────────────────────────────────────────
if __name__ == "__main__":
    from sf_auth import SalesforceAuth

    # Credentials loaded from .env file automatically
    auth = SalesforceAuth()
    auth.authenticate_simple()

    bulk = SalesforceBulkClient(auth)

    # Example: Bulk query
    job_id = bulk.create_query_job("SELECT Id, Name FROM Account LIMIT 100")
    status = bulk.wait_for_completion(job_id)
    if status.get("state") == "JobComplete":
        csv_data = bulk.get_query_results(job_id)
        print(csv_data[:500])
