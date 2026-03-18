# Governor Limits — Quick Reference Table

---

## Apex Transaction Limits

| Limit | Synchronous | Asynchronous |
|-------|:-----------:|:------------:|
| SOQL queries | **100** | **200** |
| Records retrieved (SOQL) | **50,000** | **50,000** |
| SOSL searches | **20** | **20** |
| Records retrieved (SOSL) | **2,000** | **2,000** |
| DML statements | **150** | **150** |
| Records processed (DML) | **10,000** | **10,000** |
| Callouts (HTTP) | **100** | **100** |
| Callout timeout | **120s** | **120s** |
| Future methods | **50** | **0** |
| Queueable jobs | **50** | **1** |
| Heap size | **6 MB** | **12 MB** |
| CPU time | **10,000 ms** | **60,000 ms** |
| Stack depth | **16** | **16** |
| Email invocations | **10** | **10** |

---

## API Request Limits (per 24h)

| Edition | Base | Per License | Max |
|---------|:----:|:-----------:|:---:|
| Developer | **15,000** | — | 15,000 |
| Professional | **Requires add-on** | — | — |
| Enterprise | **100,000** | +1,000 | Varies |
| Unlimited | **Unlimited** | — | — |

---

## Bulk API 2.0 Limits

| Limit | Value |
|-------|:-----:|
| Batches per 24h | **15,000** |
| Concurrent ingest jobs | **100** |
| Concurrent query jobs | **100** |
| Max file upload size | **150 MB** |
| Max record size | **10 MB** |
| Daily query data limit | **1 TB** |

---

## Streaming & Events Limits

| Limit | Value |
|-------|:-----:|
| PushTopics per org | **100** |
| Platform Events/day (Enterprise) | **25,000** |
| Platform Events/day (Unlimited) | **250,000** |
| Event retention | **72 hours** |

---

## Flow Limits

| Limit | Value |
|-------|:-----:|
| Interviews per transaction | **2,000** |
| Elements per interview | **2,000** |
| Scheduled executions/hour | **250,000** |

---

## Data & File Storage

| Edition | Data Storage | File Storage |
|---------|:------------:|:------------:|
| Developer | **5 MB** | **20 MB** |
| Enterprise | **10 GB** + 20 MB/user | **10 GB** + 612 MB/user |
| Unlimited | **10 GB** + 120 MB/user | **10 GB** + 2 GB/user |

---

## Other Limits

| Limit | Value |
|-------|:-----:|
| Composite subrequests | **25** |
| SObject Collection records | **200** |
| SOQL query result page size (REST) | **2,000** |
| Custom objects per org | **3,000** (Unlimited), **200** (Enterprise) |
| Custom fields per object | **800** (Unlimited), **500** (Enterprise) |
| Validation rules per object | **500** |
| Workflow rules per object | **500** |
| Apex classes per org | **No hard limit** (storage-based) |
| Daily email limit | **5,000** |
