# SOQL & SOSL — Salesforce Query Languages

## SOQL (Salesforce Object Query Language)

SOQL retrieves data from a **specific object**. Similar to SQL SELECT but object-oriented.

### Basic Syntax
```sql
SELECT field1, field2, ...
FROM ObjectName
[WHERE condition]
[ORDER BY field [ASC|DESC] [NULLS FIRST|LAST]]
[GROUP BY field]
[HAVING aggregate_condition]
[LIMIT n]
[OFFSET n]
```

### Simple Queries
```sql
-- Get all accounts
SELECT Id, Name, Industry, Phone FROM Account

-- Filter with WHERE
SELECT Id, Name FROM Account WHERE Industry = 'Technology'

-- Multiple conditions
SELECT Id, Name FROM Contact WHERE LastName = 'Smith' AND Account.Industry = 'Finance'

-- IN clause
SELECT Id, Name FROM Account WHERE Industry IN ('Technology', 'Finance', 'Healthcare')

-- LIKE (wildcard search)
SELECT Id, Name FROM Account WHERE Name LIKE 'Acme%'

-- NULL check
SELECT Id, Name FROM Contact WHERE Email != null

-- Limit results
SELECT Id, Name FROM Account LIMIT 10 OFFSET 5
```

### Date Literals
```sql
SELECT Id, Name FROM Opportunity WHERE CloseDate = TODAY
SELECT Id, Name FROM Account WHERE CreatedDate = LAST_WEEK
SELECT Id, Name FROM Case WHERE CreatedDate > LAST_N_DAYS:30
SELECT Id, Name FROM Opportunity WHERE CloseDate = THIS_QUARTER
```

**Available date literals:** `YESTERDAY`, `TODAY`, `TOMORROW`, `LAST_WEEK`, `THIS_WEEK`, `NEXT_WEEK`, `LAST_MONTH`, `THIS_MONTH`, `NEXT_MONTH`, `LAST_QUARTER`, `THIS_QUARTER`, `LAST_YEAR`, `THIS_YEAR`, `LAST_N_DAYS:n`, `NEXT_N_DAYS:n`, `LAST_N_MONTHS:n`, etc.

### Ordering
```sql
SELECT Id, Name, AnnualRevenue FROM Account ORDER BY AnnualRevenue DESC NULLS LAST
```

### Aggregate Functions
```sql
-- Count
SELECT COUNT() FROM Account WHERE Industry = 'Technology'
SELECT COUNT(Id) cnt FROM Account GROUP BY Industry

-- Sum, Avg, Min, Max
SELECT Industry, SUM(AnnualRevenue), AVG(AnnualRevenue)
FROM Account
GROUP BY Industry

-- HAVING (filter on aggregates)
SELECT Industry, COUNT(Id) cnt
FROM Account
GROUP BY Industry
HAVING COUNT(Id) > 5
```

---

## Relationship Queries

### Parent-to-Child (Subquery)
Get an Account with its Contacts:
```sql
SELECT Id, Name,
  (SELECT Id, FirstName, LastName, Email FROM Contacts)
FROM Account
WHERE Name = 'Acme Corp'
```

> Use the **plural relationship name** (e.g., `Contacts`, `Opportunities`, `Cases`).

### Child-to-Parent (Dot Notation)
Get Contact data with its Account info:
```sql
SELECT Id, FirstName, LastName, Account.Name, Account.Industry
FROM Contact
WHERE Account.Industry = 'Technology'
```

### Custom Relationship Names
- Parent-to-child: `Custom_Object__r` (plural: as defined in relationship field)
- Child-to-parent: `Custom_Lookup__r.FieldName`

```sql
-- Custom object relationship
SELECT Id, Name, (SELECT Id, Name FROM Custom_Children__r)
FROM Parent_Object__c

SELECT Id, Name, Parent_Lookup__r.Name
FROM Child_Object__c
```

---

## Polymorphic Relationships (Who/What)
```sql
SELECT Id, Subject, Who.Name, What.Name FROM Task
SELECT Id, Subject, 
  TYPEOF What
    WHEN Account THEN Name, Industry
    WHEN Opportunity THEN Amount, StageName
  END
FROM Task
```

---

## SOQL in REST API
```http
GET /services/data/v62.0/query/?q=SELECT+Id,Name+FROM+Account+LIMIT+5
```

## SOQL in Apex
```apex
List<Account> accounts = [SELECT Id, Name FROM Account WHERE Industry = 'Technology'];
```

---

## SOSL (Salesforce Object Search Language)

SOSL performs **text-based searches across multiple objects**. Use when you don't know which object/field contains the data.

### Basic Syntax
```sql
FIND {searchTerm}
[IN SearchGroup]
[RETURNING ObjectType(FieldList [WHERE condition] [ORDER BY field] [LIMIT n])]
[LIMIT n]
```

### Search Groups
| Group | Searches In |
|-------|-------------|
| `ALL FIELDS` | All searchable fields |
| `NAME FIELDS` | Name fields only |
| `EMAIL FIELDS` | Email fields only |
| `PHONE FIELDS` | Phone fields only |
| `SIDEBAR FIELDS` | Sidebar-visible fields |

### Examples
```sql
-- Simple search
FIND {Acme} IN ALL FIELDS RETURNING Account(Name, Id), Contact(FirstName, LastName)

-- Search with filter
FIND {John Smith} IN NAME FIELDS RETURNING Contact(Id, Name WHERE Account.Industry = 'Technology')

-- Wildcard search
FIND {Acm*} IN ALL FIELDS RETURNING Account(Name, Industry)

-- Search with limit
FIND {Cloud} IN ALL FIELDS RETURNING Account(Name LIMIT 10), Contact(Name LIMIT 5) LIMIT 20
```

### SOSL in REST API
```http
GET /services/data/v62.0/search/?q=FIND+{Acme}+IN+ALL+FIELDS+RETURNING+Account(Name,Id)
```

### SOSL in Apex
```apex
List<List<sObject>> results = [FIND 'Acme' IN ALL FIELDS RETURNING Account(Name, Id), Contact(Name)];
List<Account> accounts = (List<Account>) results[0];
List<Contact> contacts = (List<Contact>) results[1];
```

---

## SOQL vs SOSL

| Feature | SOQL | SOSL |
|---------|------|------|
| Searches | Single object (+ relationships) | Multiple objects simultaneously |
| Best for | Known object, structured queries | Text search, keyword lookup |
| Syntax | `SELECT ... FROM ...` | `FIND ... RETURNING ...` |
| Indexing | Uses object indexes | Uses search index (inverted) |
| Wildcards | `LIKE 'Acm%'` | `FIND {Acm*}` |
| Max results | 50,000 (Apex), 2,000 (API per page) | 2,000 total |
| Governor limit | 100 queries per transaction | 20 searches per transaction |
