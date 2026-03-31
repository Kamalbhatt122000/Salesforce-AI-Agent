# Salesforce Report API Reference

## Analytics API Base URL

```
{instance_url}/services/data/v62.0/analytics
```

All requests require `Authorization: Bearer {access_token}` header.

---

## Endpoints

### List Reports

```
GET /analytics/reports?pageSize=50
```

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `pageSize` | Integer | Max reports to return (default 25, max 2000) |
| `sortBy` | String | Sort field: `LastRunDate`, `Name`, `CreatedDate` |
| `hasDetailRows` | Boolean | Filter to reports with detail rows |

**Response Fields (per report)**

| Field | Description |
|-------|-------------|
| `id` | Report ID (15-char) |
| `name` | Report display name |
| `developerName` | API name |
| `description` | Report description |
| `folderName` | Folder the report lives in |
| `format` | `TABULAR`, `SUMMARY`, `MATRIX`, `MULTI_BLOCK` |
| `lastRunDate` | ISO timestamp of last execution |
| `createdBy.name` | Creator's full name |

---

### Describe Report (Metadata)

```
GET /analytics/reports/{reportId}/describe
```

**Response Structure**

```json
{
  "reportMetadata": {
    "name": "My Report",
    "reportFormat": "SUMMARY",
    "detailColumns": ["ACCOUNT_NAME", "AMOUNT", "STAGE_NAME"],
    "groupingsDown": [
      { "name": "STAGE_NAME", "sortOrder": "Asc", "dateGranularity": "NONE" }
    ],
    "reportFilters": [
      { "column": "CLOSE_DATE", "operator": "greaterThan", "value": "2024-01-01" }
    ]
  },
  "reportExtendedMetadata": {
    "detailColumnInfo": {
      "ACCOUNT_NAME": { "label": "Account Name", "dataType": "string" },
      "AMOUNT":       { "label": "Amount",       "dataType": "currency" }
    },
    "groupColumnInfo": {
      "STAGE_NAME": { "label": "Stage", "dataType": "string" }
    },
    "aggregateColumnInfo": {
      "s!AMOUNT": { "label": "Sum of Amount", "dataType": "currency" }
    }
  }
}
```

---

### Run Report (Synchronous)

```
POST /analytics/reports/{reportId}
```

**Request Body (optional — for runtime filters)**

```json
{
  "reportMetadata": {
    "reportFilters": [
      { "column": "STAGE_NAME", "operator": "equals", "value": "Prospecting" }
    ]
  }
}
```

**Response Structure**

```json
{
  "reportMetadata": { ... },
  "reportExtendedMetadata": { ... },
  "factMap": {
    "T!T": {
      "rows": [
        { "dataCells": [ { "label": "Acme Corp", "value": "001xx" }, { "label": "$50,000", "value": 50000 } ] }
      ],
      "aggregates": [
        { "label": "$1.2M", "value": 1200000 }
      ]
    }
  },
  "groupingsDown": {
    "groupings": [
      { "key": "0", "label": "Prospecting", "value": "Prospecting" }
    ]
  }
}
```

---

## factMap Key Structure

The `factMap` object uses keys to identify data sections:

| Report Format | Key Pattern | Meaning |
|---------------|-------------|---------|
| Tabular | `T!T` | All rows + grand total aggregates |
| Summary | `{groupKey}!T` | Rows for a specific group (e.g. `0!T`, `1!T`) |
| Summary | `T!T` | Grand total aggregates |
| Matrix | `{rowKey}_{colKey}!T` | Cell at row/column intersection |
| Matrix | `T!T` | Grand total |

### Reading a Tabular factMap

```
factMap["T!T"]["rows"]       → array of row objects
factMap["T!T"]["aggregates"] → array of grand total values
```

Each row has `dataCells`:
```json
{ "dataCells": [
    { "label": "Acme Corp", "value": "001xx000..." },
    { "label": "$50,000",   "value": 50000 }
]}
```

- Use `label` for display (already formatted: "$50,000", "Jan 2024")
- Use `value` for computation (raw number or ID)

### Reading a Summary factMap

```
groupingsDown.groupings[i].key   → group key (e.g. "0", "1")
factMap["{key}!T"]["rows"]       → rows in that group
factMap["{key}!T"]["aggregates"] → subtotals for that group
factMap["T!T"]["aggregates"]     → grand totals
```

---

## Filter Operators Reference

| Operator | API Value | Example Use |
|----------|-----------|-------------|
| Equals | `equals` | Status = "Open" |
| Not Equal | `notEqual` | Stage != "Closed Won" |
| Greater Than | `greaterThan` | Amount > 10000 |
| Less Than | `lessThan` | Amount < 5000 |
| Greater or Equal | `greaterOrEqual` | CloseDate >= 2024-01-01 |
| Less or Equal | `lessOrEqual` | CloseDate <= 2024-12-31 |
| Contains | `contains` | Name contains "Acme" |
| Does Not Contain | `notContain` | Name not contains "Test" |
| Starts With | `startsWith` | Name starts with "A" |
| Includes | `includes` | Picklist includes "Hot" |
| Excludes | `excludes` | Picklist excludes "Cold" |

---

## Report Folder API

```
GET /services/data/v62.0/query?q=SELECT Id, Name, Type, DeveloperName, AccessType FROM Folder WHERE Type = 'Report'
```

**Folder AccessType Values**

| Value | Meaning |
|-------|---------|
| `Public` | Visible to all users |
| `Hidden` | Private (owner only) |
| `Shared` | Shared with specific users/roles |

---

## Error Codes

| HTTP Status | Error Code | Meaning | Fix |
|-------------|------------|---------|-----|
| 400 | `INVALID_REPORT_ID` | Report ID is malformed | Check the ID format |
| 403 | `INSUFFICIENT_ACCESS` | User cannot access this report | Check folder permissions |
| 404 | `NOT_FOUND` | Report does not exist | Verify report ID from `list_reports` |
| 400 | `INVALID_FILTER_COLUMN` | Filter column API name is wrong | Use `get_report_metadata` to get correct column names |
| 400 | `INVALID_FILTER_OPERATOR` | Operator not valid for this field type | Check operator compatibility |
| 429 | `REQUEST_LIMIT_EXCEEDED` | Too many API calls | Wait and retry; check governor limits |
| 500 | `INTERNAL_SERVER_ERROR` | Salesforce-side error | Retry; if persistent, check report definition |

---

## Governor Limits

| Limit | Value |
|-------|-------|
| Synchronous report runs per hour | 500 |
| Max rows returned per run | 2,000 |
| Max runtime filters per run | 20 |
| Max report size (cells) | 100,000 |
| Async report results retention | 24 hours |

---

## Report ID Format

- Reports use **15-character IDs** starting with `00O`
- Example: `00O5g000004XXXXX`
- The `list_reports` tool returns the full ID — always use it directly
