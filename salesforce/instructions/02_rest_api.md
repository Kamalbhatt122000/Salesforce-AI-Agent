# REST API — Salesforce

## Overview

The Salesforce REST API is the most commonly used API. It provides lightweight, HTTP-based access to Salesforce data using standard methods: GET, POST, PATCH, DELETE. Responses are in JSON (default) or XML.

**Base URL Pattern:**
```
{instance_url}/services/data/v62.0/
```

## Core Endpoints

### Versions
```http
GET /services/data/
```
Returns all available API versions.

### Resources
```http
GET /services/data/v62.0/
```
Lists available resources (sobjects, query, search, etc.).

### Describe Global (All Objects)
```http
GET /services/data/v62.0/sobjects/
```
Returns metadata for all available objects.

### Describe a Specific Object
```http
GET /services/data/v62.0/sobjects/Account/describe/
```
Returns full metadata for the Account object (fields, relationships, picklist values).

---

## CRUD Operations

### Create a Record
```http
POST /services/data/v62.0/sobjects/Account/
Content-Type: application/json

{
  "Name": "Acme Corp",
  "Industry": "Technology",
  "Phone": "555-1234"
}
```
**Response:** `201 Created` with `{ "id": "001...", "success": true }`

### Read a Record
```http
GET /services/data/v62.0/sobjects/Account/001XXXXXXXXXXXX
```
Returns all fields for the record.

**Read specific fields:**
```http
GET /services/data/v62.0/sobjects/Account/001XXXXXXXXXXXX?fields=Name,Industry,Phone
```

### Update a Record
```http
PATCH /services/data/v62.0/sobjects/Account/001XXXXXXXXXXXX
Content-Type: application/json

{
  "Phone": "555-5678"
}
```
**Response:** `204 No Content` on success.

### Delete a Record
```http
DELETE /services/data/v62.0/sobjects/Account/001XXXXXXXXXXXX
```
**Response:** `204 No Content` on success.

### Upsert (Insert or Update by External ID)
```http
PATCH /services/data/v62.0/sobjects/Account/External_Id__c/EXT-001
Content-Type: application/json

{
  "Name": "Acme Corp",
  "Industry": "Technology"
}
```

---

## Query via REST

### SOQL Query
```http
GET /services/data/v62.0/query/?q=SELECT+Id,Name,Industry+FROM+Account+LIMIT+10
```

### SOSL Search
```http
GET /services/data/v62.0/search/?q=FIND+{Acme}+IN+ALL+FIELDS+RETURNING+Account(Name,Id)
```

### Query Pagination
When `nextRecordsUrl` is present in the response, fetch the next page:
```http
GET /services/data/v62.0/query/01gxx000000xxxx-2000
```

---

## Composite API

Execute multiple operations in a single request (up to 25 subrequests):

```http
POST /services/data/v62.0/composite/
Content-Type: application/json

{
  "allOrNone": true,
  "compositeRequest": [
    {
      "method": "POST",
      "url": "/services/data/v62.0/sobjects/Account/",
      "referenceId": "newAccount",
      "body": { "Name": "New Corp" }
    },
    {
      "method": "POST",
      "url": "/services/data/v62.0/sobjects/Contact/",
      "referenceId": "newContact",
      "body": {
        "LastName": "Smith",
        "AccountId": "@{newAccount.id}"
      }
    }
  ]
}
```

### SObject Tree (Create with Children)
```http
POST /services/data/v62.0/composite/tree/Account/
Content-Type: application/json

{
  "records": [
    {
      "attributes": {"type": "Account", "referenceId": "acc1"},
      "Name": "Parent Corp",
      "Contacts": {
        "records": [
          {
            "attributes": {"type": "Contact", "referenceId": "con1"},
            "LastName": "Jones"
          }
        ]
      }
    }
  ]
}
```

### Batch API
```http
POST /services/data/v62.0/composite/batch/
Content-Type: application/json

{
  "batchRequests": [
    { "method": "GET", "url": "v62.0/sobjects/Account/001xxx" },
    { "method": "GET", "url": "v62.0/sobjects/Contact/003xxx" }
  ]
}
```

---

## SObject Collections (Bulk within REST)

Operate on up to **200 records** per request:

### Create Multiple
```http
POST /services/data/v62.0/composite/sobjects
Content-Type: application/json

{
  "allOrNone": false,
  "records": [
    {"attributes": {"type": "Account"}, "Name": "Corp A"},
    {"attributes": {"type": "Account"}, "Name": "Corp B"}
  ]
}
```

### Update Multiple
```http
PATCH /services/data/v62.0/composite/sobjects
```

### Delete Multiple
```http
DELETE /services/data/v62.0/composite/sobjects?ids=001xxx,001yyy&allOrNone=false
```

---

## Invocable Actions

### List Available Actions
```http
GET /services/data/v62.0/actions/
```

### Invoke a Standard Action
```http
POST /services/data/v62.0/actions/standard/emailSimple
Content-Type: application/json

{
  "inputs": [
    {
      "emailSubject": "Test Email",
      "emailBody": "Hello from Salesforce API",
      "emailAddresses": "user@example.com"
    }
  ]
}
```

---

## Common Headers

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <access_token>` |
| `Content-Type` | `application/json` |
| `Sforce-Auto-Assign` | `FALSE` (disable assignment rules) |
| `If-Modified-Since` | Date for conditional GET |

## API Limits

- **Daily API Request Limit**: Varies by org edition (e.g., Enterprise: 100,000/day)
- **Per-request record limit**: 200 records for sObject Collections
- **Composite**: 25 subrequests per call
- **Query**: 2,000 records per page (use pagination for more)
