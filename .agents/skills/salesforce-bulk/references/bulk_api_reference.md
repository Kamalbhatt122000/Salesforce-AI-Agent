# Bulk API 2.0 Reference

## When to Use Bulk API

| Record Count | Recommended API |
|-------------|----------------|
| < 200 records | REST API (standard CRUD) |
| 200 – 2,000 records | REST API Composite |
| 2,000+ records | **Bulk API 2.0** |
| 10,000+ records | **Bulk API 2.0** (required) |

## Supported Operations

| Operation | Description | CSV Requirements |
|-----------|-------------|-----------------|
| `insert` | Create new records | All fields except `Id` |
| `update` | Update existing records | Must include `Id` column |
| `upsert` | Insert or update by external ID | Must include external ID column |
| `delete` | Soft-delete records | Only `Id` column |
| `hardDelete` | Permanently delete (no Recycle Bin) | Only `Id` column |

## Job Lifecycle

```
Open → UploadComplete → InProgress → JobComplete
                                   → Failed
                                   → Aborted
```

## API Endpoints

### Ingest Jobs (Insert/Update/Delete)

| Action | Method | Endpoint |
|--------|--------|----------|
| Create Job | `POST` | `/services/data/v62.0/jobs/ingest` |
| Upload Data | `PUT` | `/services/data/v62.0/jobs/ingest/{jobId}/batches` |
| Close Job | `PATCH` | `/services/data/v62.0/jobs/ingest/{jobId}` |
| Get Status | `GET` | `/services/data/v62.0/jobs/ingest/{jobId}` |
| Get Success Results | `GET` | `/services/data/v62.0/jobs/ingest/{jobId}/successfulResults` |
| Get Failed Results | `GET` | `/services/data/v62.0/jobs/ingest/{jobId}/failedResults` |
| Abort Job | `PATCH` | `/services/data/v62.0/jobs/ingest/{jobId}` → `{"state": "Aborted"}` |

### Query Jobs (Bulk Export)

| Action | Method | Endpoint |
|--------|--------|----------|
| Create Query Job | `POST` | `/services/data/v62.0/jobs/query` |
| Get Query Results | `GET` | `/services/data/v62.0/jobs/query/{jobId}/results` |

## Limits

| Limit | Value |
|-------|-------|
| Max file size per upload | 150 MB |
| Max records per batch | 10,000 |
| Max batches per job | 250 |
| Max concurrent ingest jobs | 4 per org |
| Max concurrent query jobs | 5 per org |
| Job processing timeout | 10 minutes per batch |
| Max API requests per 24h | Based on edition |

## CSV Formatting Rules

- First row must be the header (field API names)
- Use `CRLF` line endings
- Enclose values with commas or quotes in double quotes
- Use `#N/A` for null values (or leave empty)
- Date format: `YYYY-MM-DD`
- DateTime format: `YYYY-MM-DDThh:mm:ss.SSSZ`

## Error Handling

Common error codes in failed results:

| Error | Meaning |
|-------|---------|
| `INVALID_FIELD` | Field API name doesn't exist |
| `REQUIRED_FIELD_MISSING` | Required field not provided |
| `DUPLICATE_VALUE` | Unique field constraint violated |
| `INVALID_CROSS_REFERENCE_KEY` | Referenced record doesn't exist |
| `MALFORMED_ID` | Invalid record ID format |
