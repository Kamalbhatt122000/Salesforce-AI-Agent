---
name: salesforce-bulk
description: Guide on Salesforce Bulk API 2.0 for large-scale data operations — loading, updating, upserting, or deleting thousands to millions of records. Use when the user asks about bulk data loads, CSV imports, large-scale data migrations, or batch processing of more than 2000 records.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: data-integration
  tier: 2
  dependencies:
    - salesforce-auth
    - salesforce-crud
---

# Salesforce Bulk API Skill

Handle large-scale data operations using Bulk API 2.0.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- CSV-formatted data for ingest operations

## When to Use

| Scenario | API to Use |
|----------|-----------|
| < 200 records | REST API (standard CRUD) |
| 200 - 2,000 records | REST API Composite |
| 2,000+ records | **Bulk API 2.0** |
| 10,000+ records | **Bulk API 2.0** (required) |

## Bulk API 2.0 Workflow

### Step 1: Create a Job

```
POST /services/data/v62.0/jobs/ingest
{
  "object": "Account",
  "operation": "insert",
  "contentType": "CSV",
  "lineEnding": "CRLF"
}
```

### Step 2: Upload CSV Data

```
PUT /services/data/v62.0/jobs/ingest/{jobId}/batches
Content-Type: text/csv

Name,Industry,Phone
Acme Corp,Technology,555-0100
Globex Inc,Manufacturing,555-0200
```

### Step 3: Close the Job

```
PATCH /services/data/v62.0/jobs/ingest/{jobId}
{ "state": "UploadComplete" }
```

### Step 4: Monitor Progress

```
GET /services/data/v62.0/jobs/ingest/{jobId}
```

Job states: `Open` → `UploadComplete` → `InProgress` → `JobComplete` / `Failed`

### Step 5: Get Results

```
GET /services/data/v62.0/jobs/ingest/{jobId}/successfulResults
GET /services/data/v62.0/jobs/ingest/{jobId}/failedResults
```

## Script Usage

```python
from sf_auth import SalesforceAuth
from sf_bulk_client import SalesforceBulkClient

auth = SalesforceAuth(username=..., password=..., security_token=...)
auth.authenticate_simple()

bulk = SalesforceBulkClient(auth)

# Insert from CSV
job_id = bulk.insert_csv("Account", csv_data)
bulk.wait_for_completion(job_id)
results = bulk.get_results(job_id)
```

## Tips

- Use CSV format for best performance
- For upserts, include an external ID field
- Monitor failed results to handle errors
- Split files larger than 150 MB into multiple uploads
- Use `delete` operation carefully — always test in sandbox first

## Scripts

| Script | Purpose |
|--------|---------|
| [sf_bulk_client.py](scripts/sf_bulk_client.py) | Bulk API 2.0 job management — create, upload, poll, results |

## References

| Document | Contents |
|----------|----------|
| [Bulk API Reference](references/bulk_api_reference.md) | Endpoints, operations, CSV formatting, limits, error codes |
