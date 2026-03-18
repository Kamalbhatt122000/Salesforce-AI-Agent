# SOAP API — Salesforce

## Overview

The SOAP API uses XML-based messaging over HTTP with strict WSDL contracts. It's ideal for enterprise integrations requiring strong typing, complex transactions, and robust security. All operations are synchronous.

## WSDL Types

### Enterprise WSDL
- **Org-specific** — contains exact object and field definitions for your org
- Strong typing — all custom fields and objects are known at compile time
- Download: **Setup → API → Generate Enterprise WSDL**
- Use when: building integrations for a single org

### Partner WSDL
- **Generic** — works across any Salesforce org
- Loosely typed — uses generic `sObject` with `type` and `fields` arrays
- Download: **Setup → API → Generate Partner WSDL**
- Use when: building ISV apps or multi-org integrations

## Authentication (login)

```xml
<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:urn="urn:partner.soap.sforce.com">
  <soapenv:Body>
    <urn:login>
      <urn:username>user@example.com</urn:username>
      <urn:password>passwordSECURITY_TOKEN</urn:password>
    </urn:login>
  </soapenv:Body>
</soapenv:Envelope>
```

**Response includes:**
- `sessionId` — your access token
- `serverUrl` — endpoint for subsequent calls

## Core Operations

### Create
```xml
<urn:create>
  <urn:sObjects xsi:type="urn:Account">
    <urn:Name>Acme Corp</urn:Name>
    <urn:Industry>Technology</urn:Industry>
  </urn:sObjects>
</urn:create>
```

### Retrieve
```xml
<urn:retrieve>
  <urn:fieldList>Id, Name, Industry</urn:fieldList>
  <urn:sObjectType>Account</urn:sObjectType>
  <urn:ids>001XXXXXXXXXXXX</urn:ids>
</urn:retrieve>
```

### Update
```xml
<urn:update>
  <urn:sObjects xsi:type="urn:Account">
    <urn:Id>001XXXXXXXXXXXX</urn:Id>
    <urn:Phone>555-5678</urn:Phone>
  </urn:sObjects>
</urn:update>
```

### Delete
```xml
<urn:delete>
  <urn:ids>001XXXXXXXXXXXX</urn:ids>
</urn:delete>
```

### Upsert
```xml
<urn:upsert>
  <urn:externalIDFieldName>External_Id__c</urn:externalIDFieldName>
  <urn:sObjects xsi:type="urn:Account">
    <urn:External_Id__c>EXT-001</urn:External_Id__c>
    <urn:Name>Acme Corp</urn:Name>
  </urn:sObjects>
</urn:upsert>
```

### Query
```xml
<urn:query>
  <urn:queryString>SELECT Id, Name FROM Account LIMIT 10</urn:queryString>
</urn:query>
```

### Search (SOSL)
```xml
<urn:search>
  <urn:searchString>FIND {Acme} IN ALL FIELDS RETURNING Account(Name, Id)</urn:searchString>
</urn:search>
```

## Describe Operations

### describeSObject
Returns full metadata for a specific object:
```xml
<urn:describeSObject>
  <urn:sObjectType>Account</urn:sObjectType>
</urn:describeSObject>
```

### describeGlobal
Returns a list of all objects available in the org.

### describeLayout
Returns the page layout metadata for an object.

## SOAP Headers

| Header | Purpose |
|--------|---------|
| `SessionHeader` | Contains `sessionId` for authentication |
| `QueryOptions` | `batchSize` to control records per query batch (200–2000) |
| `AllOrNoneHeader` | If `true`, all records in batch succeed or all fail |
| `AssignmentRuleHeader` | Specify custom assignment rules |
| `MruHeader` | Update Most Recently Used list |
| `AllowFieldTruncationHeader` | Allow truncation instead of error for too-long values |

## Error Handling

SOAP faults return structured XML:
```xml
<soapenv:Fault>
  <faultcode>sf:INVALID_SESSION_ID</faultcode>
  <faultstring>Session expired or invalid</faultstring>
</soapenv:Fault>
```

Common fault codes:
- `INVALID_SESSION_ID` — re-authenticate
- `INVALID_FIELD` — field doesn't exist on object
- `MALFORMED_QUERY` — SOQL syntax error
- `INSUFFICIENT_ACCESS` — user lacks permissions

## When to Use SOAP vs REST

| SOAP | REST |
|------|------|
| Strict contract needed | Flexible, lightweight |
| Enterprise/legacy systems | Web/mobile apps |
| Strong typing via WSDL | JSON-based, easy to parse |
| Complex multi-object transactions | Simple CRUD |
