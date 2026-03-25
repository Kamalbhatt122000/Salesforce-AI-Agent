# Automation & Development — Apex Patterns Reference

## Trigger Handler Pattern

Always use a handler class to keep triggers clean and testable.

### Trigger

```apex
trigger AccountTrigger on Account (before insert, before update, after insert, after update) {
    if (Trigger.isBefore) {
        if (Trigger.isInsert) {
            AccountTriggerHandler.beforeInsert(Trigger.new);
        }
        if (Trigger.isUpdate) {
            AccountTriggerHandler.beforeUpdate(Trigger.new, Trigger.oldMap);
        }
    }
    if (Trigger.isAfter) {
        if (Trigger.isInsert) {
            AccountTriggerHandler.afterInsert(Trigger.new);
        }
    }
}
```

### Handler

```apex
public class AccountTriggerHandler {
    public static void beforeInsert(List<Account> newAccounts) {
        for (Account acc : newAccounts) {
            if (String.isBlank(acc.Description)) {
                acc.Description = 'Created via automation';
            }
        }
    }
    
    public static void beforeUpdate(List<Account> newAccounts, Map<Id, Account> oldMap) {
        for (Account acc : newAccounts) {
            Account oldAcc = oldMap.get(acc.Id);
            if (acc.Industry != oldAcc.Industry) {
                acc.Description = 'Industry changed from ' + oldAcc.Industry + ' to ' + acc.Industry;
            }
        }
    }
}
```

### Test Class

```apex
@isTest
public class AccountTriggerHandlerTest {
    @isTest
    static void testBeforeInsert() {
        Account acc = new Account(Name = 'Test Account');
        
        Test.startTest();
        insert acc;
        Test.stopTest();
        
        Account result = [SELECT Description FROM Account WHERE Id = :acc.Id];
        System.assertEquals('Created via automation', result.Description);
    }
}
```

## Async Apex Patterns

| Type | Use Case | Limits |
|------|----------|--------|
| **@future** | Simple async callout or computation | 50 calls per transaction |
| **Queueable** | Chained async jobs with complex data | 50 jobs per transaction |
| **Batch** | Process large datasets (50K+ records) | 5 active batches per org |
| **Scheduled** | Time-based recurring jobs | 100 scheduled classes per org |

## Flow Types

| Type | Trigger | Use Case |
|------|---------|----------|
| **Screen Flow** | User clicks button | Guided wizards, data entry forms |
| **Record-Triggered** | Record DML | Auto-update fields, send notifications |
| **Scheduled** | Time-based | Daily/weekly batch processing |
| **Auto-Launched** | Called by other automation | Sub-flows, reusable logic |

## Governor Limits (Critical)

| Limit | Synchronous | Asynchronous |
|-------|-------------|--------------|
| SOQL queries | 100 | 200 |
| DML statements | 150 | 150 |
| Records retrieved | 50,000 | 50,000 |
| Callouts | 100 | 100 |
| CPU time | 10,000 ms | 60,000 ms |
| Heap size | 6 MB | 12 MB |
| Future calls | 50 | 50 |
| Queueable jobs | 50 | 1 |

## Best Practices

1. **Bulkify everything** — Never put SOQL or DML inside loops
2. **One trigger per object** — Use handler pattern to manage logic
3. **75% code coverage** — Required for production deployment
4. **Use async for heavy work** — Callouts, large data processing
5. **Governor-limit aware** — Always check limits before processing
6. **Test negative cases** — Test error scenarios, not just happy path
7. **Use Custom Metadata** — Instead of hardcoding config values
