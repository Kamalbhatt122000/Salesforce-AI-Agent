# Apex Development — Salesforce

## Overview

Apex is Salesforce's proprietary, strongly-typed, object-oriented programming language (similar to Java/C#). It runs on Salesforce servers and is used for custom business logic, triggers, REST/SOAP services, and batch processing.

## Apex Classes

### Basic Class
```apex
public class AccountService {
    
    public static List<Account> getActiveAccounts() {
        return [SELECT Id, Name, Industry FROM Account WHERE IsDeleted = false LIMIT 100];
    }
    
    public static Account createAccount(String name, String industry) {
        Account acc = new Account(Name = name, Industry = industry);
        insert acc;
        return acc;
    }
    
    public static void updateAccountIndustry(Id accountId, String newIndustry) {
        Account acc = [SELECT Id FROM Account WHERE Id = :accountId];
        acc.Industry = newIndustry;
        update acc;
    }
}
```

### Access Modifiers
| Modifier | Visibility |
|----------|------------|
| `private` | Same class only (default) |
| `public` | Same namespace |
| `global` | All namespaces (required for web services) |
| `protected` | Same class and subclasses |

---

## Triggers

Triggers execute code in response to DML events on records.

### Trigger Syntax
```apex
trigger AccountTrigger on Account (before insert, before update, after insert, after update, after delete) {
    
    if (Trigger.isBefore && Trigger.isInsert) {
        for (Account acc : Trigger.new) {
            if (String.isBlank(acc.Industry)) {
                acc.Industry = 'Other';
            }
        }
    }
    
    if (Trigger.isAfter && Trigger.isInsert) {
        AccountTriggerHandler.onAfterInsert(Trigger.new);
    }
}
```

### Trigger Context Variables
| Variable | Description |
|----------|-------------|
| `Trigger.new` | List of new records (insert/update) |
| `Trigger.old` | List of old records (update/delete) |
| `Trigger.newMap` | Map of ID → new record |
| `Trigger.oldMap` | Map of ID → old record |
| `Trigger.isBefore` | True if before trigger |
| `Trigger.isAfter` | True if after trigger |
| `Trigger.isInsert` | True if insert operation |
| `Trigger.isUpdate` | True if update operation |
| `Trigger.isDelete` | True if delete operation |
| `Trigger.size` | Number of records |

### Trigger Best Practices
1. **One trigger per object** — use handler classes
2. **Bulkify** — always handle lists, never single records
3. **Avoid SOQL/DML in loops** — causes governor limit errors
4. **Use trigger frameworks** — for recursion prevention

---

## DML Operations

```apex
// Insert
Account acc = new Account(Name = 'Acme');
insert acc;

// Update
acc.Industry = 'Technology';
update acc;

// Upsert (by External ID)
Account acc2 = new Account(External_Id__c = 'EXT-001', Name = 'Beta');
upsert acc2 External_Id__c;

// Delete
delete acc;

// Undelete
undelete acc;

// Database methods (partial success)
Database.SaveResult[] results = Database.insert(accountList, false);
for (Database.SaveResult sr : results) {
    if (!sr.isSuccess()) {
        for (Database.Error err : sr.getErrors()) {
            System.debug('Error: ' + err.getMessage());
        }
    }
}
```

---

## Asynchronous Apex

### Future Methods
```apex
public class AsyncService {
    @future(callout=true)
    public static void makeExternalCallout(String endpoint) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(endpoint);
        req.setMethod('GET');
        Http http = new Http();
        HttpResponse res = http.send(req);
    }
}
```

### Queueable Apex
```apex
public class AccountProcessor implements Queueable {
    private List<Account> accounts;
    
    public AccountProcessor(List<Account> accounts) {
        this.accounts = accounts;
    }
    
    public void execute(QueueableContext context) {
        for (Account acc : accounts) {
            acc.Description = 'Processed on ' + System.now();
        }
        update accounts;
    }
}

// Enqueue
System.enqueueJob(new AccountProcessor(accountList));
```

### Batch Apex
```apex
public class AccountBatch implements Database.Batchable<sObject> {
    
    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator('SELECT Id, Name FROM Account WHERE Industry = null');
    }
    
    public void execute(Database.BatchableContext bc, List<Account> scope) {
        for (Account acc : scope) {
            acc.Industry = 'Unknown';
        }
        update scope;
    }
    
    public void finish(Database.BatchableContext bc) {
        System.debug('Batch completed');
    }
}

// Execute with batch size 200
Database.executeBatch(new AccountBatch(), 200);
```

### Scheduled Apex
```apex
public class WeeklyAccountCleanup implements Schedulable {
    public void execute(SchedulableContext sc) {
        Database.executeBatch(new AccountBatch(), 200);
    }
}

// Schedule: every Monday at 6 AM
String cronExp = '0 0 6 ? * MON';
System.schedule('Weekly Account Cleanup', cronExp, new WeeklyAccountCleanup());
```

---

## Custom REST Endpoints

```apex
@RestResource(urlMapping='/accounts/*')
global class AccountRestService {
    
    @HttpGet
    global static Account getAccount() {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substringAfterLast('/');
        return [SELECT Id, Name, Industry FROM Account WHERE Id = :accountId];
    }
    
    @HttpPost
    global static String createAccount(String name, String industry) {
        Account acc = new Account(Name = name, Industry = industry);
        insert acc;
        return acc.Id;
    }
    
    @HttpPatch
    global static Account updateAccount(String industry) {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substringAfterLast('/');
        Account acc = [SELECT Id FROM Account WHERE Id = :accountId];
        acc.Industry = industry;
        update acc;
        return acc;
    }
    
    @HttpDelete
    global static void deleteAccount() {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substringAfterLast('/');
        Account acc = [SELECT Id FROM Account WHERE Id = :accountId];
        delete acc;
    }
}
```

**Access via:**
```
{instance_url}/services/apexrest/accounts/001XXXXXXXXXXXX
```

---

## Test Classes

Salesforce requires **75% code coverage** for production deployment.

```apex
@isTest
public class AccountServiceTest {
    
    @TestSetup
    static void setup() {
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < 5; i++) {
            accounts.add(new Account(Name = 'Test Account ' + i, Industry = 'Technology'));
        }
        insert accounts;
    }
    
    @isTest
    static void testGetActiveAccounts() {
        Test.startTest();
        List<Account> result = AccountService.getActiveAccounts();
        Test.stopTest();
        
        System.assertEquals(5, result.size(), 'Should return 5 accounts');
    }
    
    @isTest
    static void testCreateAccount() {
        Test.startTest();
        Account acc = AccountService.createAccount('New Corp', 'Finance');
        Test.stopTest();
        
        System.assertNotEquals(null, acc.Id, 'Account should have an Id');
        Account queried = [SELECT Industry FROM Account WHERE Id = :acc.Id];
        System.assertEquals('Finance', queried.Industry);
    }
}
```

### Test Best Practices
- Use `@TestSetup` for shared test data
- Wrap test logic in `Test.startTest()` / `Test.stopTest()`
- Use `System.assert*` methods for validation
- Test bulk scenarios (200+ records)
- Test negative cases and error handling
- Use `Test.setMock()` for HTTP callout mocks
