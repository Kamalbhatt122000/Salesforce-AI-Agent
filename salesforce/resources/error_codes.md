# Salesforce API Error Codes

Common error codes and their resolutions.

---

## HTTP Status Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| `200` | OK | Successful GET/POST |
| `201` | Created | Record created successfully |
| `204` | No Content | Successful PATCH/DELETE |
| `300` | Multiple Choices | External ID matches multiple records |
| `400` | Bad Request | Malformed request, invalid field/value |
| `401` | Unauthorized | Invalid or expired token |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Object/record doesn't exist |
| `405` | Method Not Allowed | Wrong HTTP method for endpoint |
| `415` | Unsupported Media Type | Missing/wrong Content-Type header |
| `500` | Internal Server Error | Salesforce-side error |
| `503` | Service Unavailable | Salesforce maintenance/overloaded |

---

## Salesforce Error Codes

### Authentication Errors

| Error Code | Message | Fix |
|-----------|---------|-----|
| `INVALID_SESSION_ID` | Session expired or invalid | Re-authenticate to get new token |
| `INVALID_LOGIN` | Invalid username/password/token | Check credentials; add security token to password |
| `LOGIN_MUST_USE_SECURITY_TOKEN` | Security token required | Append security token to password |
| `INVALID_CLIENT` | Invalid client_id | Check Connected App Consumer Key |
| `INVALID_GRANT` | Authentication failure | Check OAuth flow parameters |
| `API_DISABLED_FOR_ORG` | API access not enabled | Enable API access in org settings |

### Data Errors

| Error Code | Message | Fix |
|-----------|---------|-----|
| `REQUIRED_FIELD_MISSING` | Required field not provided | Include all required fields |
| `FIELD_INTEGRITY_EXCEPTION` | Invalid field value | Check data type, length, format |
| `INVALID_FIELD` | Field doesn't exist | Verify API field name |
| `DUPLICATE_VALUE` | Unique constraint violated | Check for duplicate external ID or unique field |
| `ENTITY_IS_DELETED` | Record in recycle bin | Undelete the record or use a different one |
| `INVALID_CROSS_REFERENCE_KEY` | Invalid relationship reference | Verify referenced record exists and is accessible |
| `INVALID_TYPE` | Unknown object type | Verify API object name (e.g., `Account`, not `Accounts`) |
| `MALFORMED_ID` | Invalid Salesforce ID | IDs must be 15 or 18 characters |
| `STRING_TOO_LONG` | Value exceeds field length | Truncate value or use a longer field type |

### Permission Errors

| Error Code | Message | Fix |
|-----------|---------|-----|
| `INSUFFICIENT_ACCESS_OR_READONLY` | No access to record/field | Check profile permissions, sharing rules |
| `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY` | No access to related record | Check permissions on parent/lookup records |
| `FIELD_CUSTOM_VALIDATION_EXCEPTION` | Validation rule failed | Check validation rule criteria |
| `CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY` | Trigger/flow runtime error | Check Apex trigger or Flow logic |

### Limit Errors

| Error Code | Message | Fix |
|-----------|---------|-----|
| `REQUEST_LIMIT_EXCEEDED` | Daily API limit reached | Use Composite API, Bulk API; optimize calls |
| `QUERY_TIMEOUT` | SOQL query took too long | Add selective filters, add indexes |
| `TOO_MANY_SOQL_QUERIES` | 100+ SOQL queries/transaction | Move queries outside loops |
| `TOO_MANY_DML_STATEMENTS` | 150+ DML ops/transaction | Collect records and do bulk DML |
| `APEX_CPU_TIME_LIMIT_EXCEEDED` | CPU time > 10s (sync) | Optimize loops, reduce complexity |
| `HEAP_SIZE_LIMIT_EXCEEDED` | Heap > 6MB (sync) | Reduce data in memory, use lazy loading |

### Bulk API Errors

| Error Code | Message | Fix |
|-----------|---------|-----|
| `InvalidBatch` | Batch operation failed | Check CSV format, header row |
| `InvalidJob` | Job in invalid state | Job may be closed/aborted, create a new one |
| `ExceededQuota` | Bulk API quota exceeded | Wait for next 24-hour window |

---

## Debugging Tips

1. **Check response body** — Salesforce error responses include detailed messages
2. **Enable debug logs** — Setup → Debug Logs → Add trace flag for your user
3. **Use Workbench** — Test API calls interactively at workbench.developerforce.com
4. **Check API header** `Sforce-Limit-Info: api-usage=47/100000`
5. **Review Apex Logs** — Developer Console → Logs → View recent logs
