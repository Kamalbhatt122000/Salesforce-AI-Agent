# Governor Limits — Salesforce

## Overview

Salesforce is a **multi-tenant** platform. Governor limits prevent any single tenant from monopolizing shared resources. These limits apply per-transaction (synchronous or asynchronous).

---

## Apex Execution Limits

| Limit | Synchronous | Asynchronous |
|-------|-------------|--------------|
| **SOQL queries** | 100 | 200 |
| **Records retrieved (SOQL)** | 50,000 | 50,000 |
| **SOSL searches** | 20 | 20 |
| **Records retrieved (SOSL)** | 2,000 | 2,000 |
| **DML statements** | 150 | 150 |
| **Records processed (DML)** | 10,000 | 10,000 |
| **Callouts (HTTP/Web Service)** | 100 | 100 |
| **Callout timeout** | 120 seconds | 120 seconds |
| **Total callout time** | 120 seconds | 120 seconds |
| **Heap size** | 6 MB | 12 MB |
| **CPU time** | 10,000 ms | 60,000 ms |
| **Stack depth** | 16 | 16 |
| **Future method invocations** | 50 | 0 (can't call future from future) |
| **Queueable jobs added** | 50 | 1 |
| **sendEmail invocations** | 10 | 10 |
| **Total email recipients** | 5,000/day | 5,000/day |

---

## API Limits

| Limit | Value |
|-------|-------|
| **Daily API requests** | Based on edition + user licenses |
| • Developer Edition | 15,000/day |
| • Enterprise Edition | 100,000/day + 1,000 per user license |
| • Unlimited Edition | Unlimited (within reason) |
| **Concurrent API requests** | 25 long-running |
| **API request size** | 50 MB |
| **API response size** | 50 MB |
| **Query results per page (REST)** | 2,000 records |
| **Composite subrequests** | 25 per call |
| **SObject Collection records** | 200 per call |

---

## Bulk API Limits

| Limit | Value |
|-------|-------|
| **Batches per 24-hour period** | 15,000 |
| **Concurrent ingest jobs** | 100 |
| **Concurrent query jobs** | 100 |
| **File upload size** | 150 MB |
| **Record size** | 10 MB |
| **Daily bulk query data** | 1 TB |

---

## Streaming API Limits

| Limit | Value |
|-------|-------|
| **PushTopics per org** | 100 |
| **Platform Events daily** | Varies by edition (25K Enterprise) |
| **CDC events/hour** | Varies by edition |
| **Concurrent CometD clients** | Based on edition |
| **Event retention** | 72 hours |

---

## Flow Limits

| Limit | Value |
|-------|-------|
| **Flow interviews per transaction** | 2,000 |
| **Executed elements per interview** | 2,000 |
| **Scheduled flow executions/hour** | 250,000 |

---

## Data Storage Limits

| Edition | Data Storage | File Storage |
|---------|-------------|--------------|
| Developer | 5 MB | 20 MB |
| Enterprise | 10 GB + 20 MB/user | 10 GB + 612 MB/user |
| Unlimited | 10 GB + 120 MB/user | 10 GB + 2 GB/user |

---

## Common Limit Errors & Solutions

### `System.LimitException: Too many SOQL queries: 101`
**Cause:** More than 100 SOQL queries in one transaction.
**Fix:** Move queries outside of loops. Use relationship queries and collections.

```apex
// BAD — query inside loop
for (Account acc : accounts) {
    List<Contact> cons = [SELECT Id FROM Contact WHERE AccountId = :acc.Id]; // ❌
}

// GOOD — single query with collection
Map<Id, Account> accountMap = new Map<Id, Account>(
    [SELECT Id, (SELECT Id FROM Contacts) FROM Account WHERE Id IN :accountIds]  // ✅
);
```

### `System.LimitException: Too many DML statements: 151`
**Cause:** More than 150 DML operations.
**Fix:** Collect records into lists and do bulk DML.

```apex
// BAD
for (Account acc : accounts) {
    update acc;  // ❌
}

// GOOD
update accounts;  // ✅ single DML for all records
```

### `System.LimitException: Apex CPU time limit exceeded`
**Cause:** Code took > 10 seconds (sync) or > 60 seconds (async).
**Fix:** Optimize loops, reduce complexity, move to async.

### `System.CalloutException: Read timed out`
**Cause:** External service didn't respond within 120 seconds.
**Fix:** Increase timeout, optimize external service, use async.

### `REQUEST_LIMIT_EXCEEDED`
**Cause:** Daily API request limit reached.
**Fix:** Optimize API calls, use Composite API, use Bulk API for large operations.

---

## Checking Limits in Apex

```apex
System.debug('SOQL queries used: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
System.debug('DML statements used: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
System.debug('CPU time used: ' + Limits.getCpuTime() + '/' + Limits.getLimitCpuTime());
System.debug('Heap size used: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize());
System.debug('Callouts used: ' + Limits.getCallouts() + '/' + Limits.getLimitCallouts());
```

## Checking Limits via API

Response header `Sforce-Limit-Info`:
```
Sforce-Limit-Info: api-usage=47/100000
```
