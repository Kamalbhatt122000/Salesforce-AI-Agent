# Reports & Dashboards — Salesforce

## Overview

Salesforce provides built-in analytics through Reports and Dashboards. The **Analytics API** allows programmatic access to run reports, get results, and manage dashboards.

## Report Types

| Type | Description |
|------|-------------|
| **Tabular** | Simple list of records (no grouping) |
| **Summary** | Records grouped by rows |
| **Matrix** | Records grouped by rows AND columns |
| **Joined** | Multiple report blocks in one report |

---

## Analytics REST API

### List Reports
```http
GET /services/data/v62.0/analytics/reports
```

### Get Report Metadata
```http
GET /services/data/v62.0/analytics/reports/{reportId}/describe
```

### Run a Report
```http
GET /services/data/v62.0/analytics/reports/{reportId}
```

### Run with Filters (POST)
```http
POST /services/data/v62.0/analytics/reports/{reportId}
Content-Type: application/json

{
  "reportMetadata": {
    "reportFilters": [
      {
        "column": "INDUSTRY",
        "operator": "equals",
        "value": "Technology"
      }
    ]
  }
}
```

### Run Asynchronously
```http
POST /services/data/v62.0/analytics/reports/{reportId}/instances
```

**Check status:**
```http
GET /services/data/v62.0/analytics/reports/{reportId}/instances/{instanceId}
```

---

## Report Response Structure

```json
{
  "reportMetadata": {
    "name": "Accounts by Industry",
    "reportFormat": "SUMMARY",
    "detailColumns": ["ACCOUNT.NAME", "INDUSTRY", "PHONE"]
  },
  "factMap": {
    "0!T": {
      "rows": [
        { "dataCells": [{"label": "Acme Corp", "value": "001xxx"}, ...] }
      ],
      "aggregates": [{"label": "5", "value": 5}]
    }
  },
  "groupingsDown": {
    "groupings": [
      {"label": "Technology", "value": "Technology", "key": "0"}
    ]
  }
}
```

### Understanding factMap Keys
- `T` = Grand Total row
- `0!T` = First grouping's total
- `0_0!T` = Sub-grouping total
- `0_0` = Individual data row

---

## Dashboards API

### List Dashboards
```http
GET /services/data/v62.0/analytics/dashboards
```

### Get Dashboard Data
```http
GET /services/data/v62.0/analytics/dashboards/{dashboardId}
```

### Refresh Dashboard
```http
PUT /services/data/v62.0/analytics/dashboards/{dashboardId}
```

### Dashboard Status
```http
GET /services/data/v62.0/analytics/dashboards/{dashboardId}/status
```

---

## Report via SOQL

You can also query report-related objects:
```sql
SELECT Id, Name, DeveloperName, FolderName FROM Report WHERE DeveloperName = 'My_Custom_Report'
```

## Report Builder Tips

- Use **Cross Filters** to find records with/without related records
- **Bucket Fields** group values without creating formulas
- **Row-Level Formulas** add calculated columns
- **Historical Trending** tracks field changes over time
- **Joined Reports** combine data from multiple report types
