# Bulk API 2.0 — Salesforce

## Overview

The Bulk API is designed for processing large datasets asynchronously (2,000+ records). It uses a simplified RESTful interface and CSV data format. Operations: insert, update, upsert, delete, hard delete.

**Base URL:**
```
{instance_url}/services/data/v62.0/jobs/ingest/
```

## Job Lifecycle

```
Create Job → Upload Data (CSV) → Close Job → Poll Status → Get Results
```

## Step-by-Step

### 1. Create a Job

```http
POST /services/data/v62.0/jobs/ingest/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "object": "Account",
  "operation": "insert",
  "contentType": "CSV",
  "lineEnding": "CRLF"
}
```

**Operations:** `insert`, `update`, `upsert`, `delete`, `hardDelete`

For **upsert**, add:
```json
{
  "object": "Account",
  "operation": "upsert",
  "externalIdFieldName": "External_Id__c",
  "contentType": "CSV"
}
```

**Response:**
```json
{
  "id": "750xx0000000001",
  "operation": "insert",
  "object": "Account",
  "state": "Open",
  "contentType": "CSV"
}
```

### 2. Upload CSV Data

```http
PUT /services/data/v62.0/jobs/ingest/750xx0000000001/batches/
Content-Type: text/csv
Authorization: Bearer <access_token>

Name,Industry,Phone
"Acme Corp","Technology","555-1234"
"Beta Inc","Finance","555-5678"
```

> **Max upload size:** 150 MB per request. Split larger files into multiple uploads.

### 3. Close the Job

```http
PATCH /services/data/v62.0/jobs/ingest/750xx0000000001
Content-Type: application/json

{
  "state": "UploadComplete"
}
```

### 4. Poll Job Status

```http
GET /services/data/v62.0/jobs/ingest/750xx0000000001
```

**States:**
| State | Meaning |
|-------|---------|
| `Open` | Accepting data |
| `UploadComplete` | Data uploaded, processing |
| `InProgress` | Salesforce is processing |
| `JobComplete` | All records processed |
| `Failed` | Job failed |
| `Aborted` | Job was cancelled |

### 5. Get Results

**Successful records:**
```http
GET /services/data/v62.0/jobs/ingest/750xx0000000001/successfulResults/
Accept: text/csv
```

**Failed records:**
```http
GET /services/data/v62.0/jobs/ingest/750xx0000000001/failedResults/
Accept: text/csv
```

**Unprocessed records:**
```http
GET /services/data/v62.0/jobs/ingest/750xx0000000001/unprocessedrecords/
Accept: text/csv
```

---

## Bulk Query

For extracting large volumes of data:

### Create Query Job
```http
POST /services/data/v62.0/jobs/query/
Content-Type: application/json

{
  "operation": "query",
  "query": "SELECT Id, Name, Industry FROM Account"
}
```

For deleted/archived records: `"operation": "queryAll"`

### Get Query Results
```http
GET /services/data/v62.0/jobs/query/750xx0000000001/results
Accept: text/csv
```

Use `maxRecords` and `locator` for pagination:
```http
GET /services/data/v62.0/jobs/query/750xx/results?maxRecords=50000&locator=<locator>
```

---

## Job Management

### List All Jobs
```http
GET /services/data/v62.0/jobs/ingest/
```

### Abort a Job
```http
PATCH /services/data/v62.0/jobs/ingest/750xx0000000001
Content-Type: application/json

{ "state": "Aborted" }
```

### Delete a Job
```http
DELETE /services/data/v62.0/jobs/ingest/750xx0000000001
```

---

## Limits & Best Practices

| Limit | Value |
|-------|-------|
| Max file size per upload | 150 MB |
| Max record size | 10 MB |
| Max fields per record | 5,000 |
| Daily bulk API batches | 15,000 |
| Concurrent bulk API jobs | 100 (query), 100 (ingest) |

**Best Practices:**
- Use CSV format (most efficient)
- Split files > 100 MB into chunks
- Poll status every 15–30 seconds
- Always check `failedResults` after job completion
- Use `hardDelete` cautiously (bypasses recycle bin)
