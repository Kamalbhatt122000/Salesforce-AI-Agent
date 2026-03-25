---
name: salesforce-automation
description: Guide on Salesforce automation tools — Apex development (classes, triggers, test classes, async Apex), Flows (screen flows, record-triggered flows, scheduled flows), Process Builder, and Workflow Rules. Use when the user asks about writing Apex code, creating triggers, building flows, or implementing automation logic.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: development
  tier: 3
  dependencies:
    - salesforce-auth
    - salesforce-schema
---

# Salesforce Automation & Development Skill

Write Apex code, design Flows, and implement automation on the Salesforce platform.

## Scope

This skill covers **guidance and code generation** for:
- Apex classes, triggers, and test classes
- Async Apex (Future, Queueable, Batch, Scheduled)
- Flows (Screen, Record-Triggered, Scheduled, Auto-Launched)
- Governor limits awareness

> **Note**: This skill provides code and instructions. The code must be deployed to the Salesforce org via the Tooling API, Metadata API, or Salesforce Setup UI.

## Apex Development

### Trigger Template

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

### Handler Pattern

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

### Test Class Template

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

## Flow Types

| Type | Trigger | Use Case |
|------|---------|----------|
| **Screen Flow** | User clicks button | Guided wizards, data entry forms |
| **Record-Triggered** | Record DML | Auto-update fields, send notifications |
| **Scheduled** | Time-based | Daily/weekly batch processing |
| **Auto-Launched** | Called by other automation | Sub-flows, reusable components |

## Governor Limits (Key Ones)

| Limit | Value |
|-------|-------|
| SOQL queries per transaction | 100 |
| DML statements per transaction | 150 |
| Records retrieved by SOQL | 50,000 |
| Callouts per transaction | 100 |
| CPU time limit | 10,000 ms |
| Heap size | 6 MB (sync), 12 MB (async) |

## Best Practices

- **Bulkify** all triggers — never use SOQL/DML inside loops
- Use **trigger handler pattern** to keep triggers clean
- Write **test classes** with at least 75% code coverage
- Use **async Apex** for heavy operations
- Be **governor limit aware** in every piece of code

## References

| Document | Contents |
|----------|----------|
| [Apex Patterns](references/apex_patterns.md) | Trigger handler pattern, async Apex types, flow types, governor limits table |
