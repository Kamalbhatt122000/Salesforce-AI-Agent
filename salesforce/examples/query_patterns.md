# Example: Common SOQL Query Patterns

---

## Basic Queries

```sql
-- Get all accounts
SELECT Id, Name, Industry, Phone FROM Account

-- Filter by a field value
SELECT Id, Name FROM Account WHERE Industry = 'Technology'

-- Multiple filters
SELECT Id, Name, Email FROM Contact WHERE LastName = 'Smith' AND MailingCity = 'San Francisco'

-- OR conditions
SELECT Id, Name FROM Account WHERE Industry = 'Technology' OR Industry = 'Finance'

-- IN list
SELECT Id, Name FROM Account WHERE Industry IN ('Technology', 'Finance', 'Healthcare')

-- NOT IN
SELECT Id, Name FROM Account WHERE Industry NOT IN ('Government', 'Non-Profit')

-- Wildcard (LIKE)
SELECT Id, Name FROM Account WHERE Name LIKE 'Acme%'
SELECT Id, Name FROM Contact WHERE Email LIKE '%@gmail.com'
```

---

## Date Filters

```sql
-- Records created today
SELECT Id, Name FROM Account WHERE CreatedDate = TODAY

-- Created in the last 30 days
SELECT Id, Name FROM Opportunity WHERE CreatedDate = LAST_N_DAYS:30

-- Closing this quarter
SELECT Id, Name, Amount FROM Opportunity WHERE CloseDate = THIS_QUARTER

-- Modified yesterday
SELECT Id, Name FROM Account WHERE LastModifiedDate = YESTERDAY

-- Created this year
SELECT Id, Name FROM Lead WHERE CreatedDate = THIS_YEAR
```

---

## Sorting and Limiting

```sql
-- Sort by revenue descending
SELECT Id, Name, AnnualRevenue FROM Account ORDER BY AnnualRevenue DESC NULLS LAST

-- Multiple sort fields
SELECT Id, Name, Industry FROM Account ORDER BY Industry ASC, Name ASC

-- Pagination with LIMIT and OFFSET
SELECT Id, Name FROM Account ORDER BY Name LIMIT 10 OFFSET 20
```

---

## Aggregate Queries

```sql
-- Count records
SELECT COUNT() FROM Account
SELECT COUNT() FROM Account WHERE Industry = 'Technology'

-- Count with grouping
SELECT Industry, COUNT(Id) total FROM Account GROUP BY Industry ORDER BY COUNT(Id) DESC

-- Sum and Average
SELECT Industry, SUM(AnnualRevenue), AVG(AnnualRevenue) FROM Account GROUP BY Industry

-- Min and Max
SELECT MIN(CreatedDate) earliest, MAX(CreatedDate) latest FROM Account

-- HAVING filter (on aggregates)
SELECT Industry, COUNT(Id) cnt FROM Account GROUP BY Industry HAVING COUNT(Id) > 10
```

---

## Relationship Queries

### Parent-to-Child (Get children with parent)

```sql
-- Account with its Contacts
SELECT Id, Name,
    (SELECT Id, FirstName, LastName, Email FROM Contacts)
FROM Account
WHERE Name = 'Acme Corp'

-- Account with its Opportunities
SELECT Id, Name,
    (SELECT Id, Name, Amount, StageName FROM Opportunities WHERE StageName = 'Closed Won')
FROM Account

-- Account with Cases
SELECT Id, Name,
    (SELECT Id, Subject, Status FROM Cases WHERE Status = 'Open')
FROM Account
WHERE Id = '001xxx'
```

### Child-to-Parent (Get parent info from child)

```sql
-- Contact with Account name
SELECT Id, FirstName, LastName, Account.Name, Account.Industry
FROM Contact

-- Opportunity with Account info
SELECT Id, Name, Amount, Account.Name, Account.Industry
FROM Opportunity
WHERE Account.Industry = 'Technology'

-- Case with Contact and Account info
SELECT Id, Subject, Contact.Name, Account.Name
FROM Case
WHERE Status = 'Open'
```

---

## Advanced Patterns

### Records with NO children
```sql
-- Accounts with no Contacts (anti-join via subquery in Apex/Flow)
SELECT Id, Name FROM Account WHERE Id NOT IN (SELECT AccountId FROM Contact WHERE AccountId != null)
```

### Polymorphic queries (Task/Event)
```sql
-- Tasks with who/what info
SELECT Id, Subject, Who.Name, What.Name, Status FROM Task WHERE Status = 'Open'
```

### Formula fields and calculated values
```sql
-- Records where a formula field meets criteria
SELECT Id, Name, Days_Since_Last_Activity__c FROM Account WHERE Days_Since_Last_Activity__c > 90
```

### Date/Time comparisons
```sql
-- Records modified in the last hour
SELECT Id, Name FROM Account WHERE LastModifiedDate > 2025-01-15T10:00:00Z
```

---

## Using with Python

```python
from sf_auth import SalesforceAuth
from sf_query import SalesforceQuery

auth = SalesforceAuth(
    username="priyanka.joshi547@agentforce.com",
    password="Priyanka21#",
    security_token="vHnao3amdKeuFFObAVVuqmluH",
)
auth.authenticate_simple()
q = SalesforceQuery(auth)

# Run any SOQL
results = q.soql("SELECT Id, Name, Industry FROM Account LIMIT 10")
for r in results:
    print(f"  {r['Name']} - {r.get('Industry', 'N/A')}")

# Count
q.count("Account", "Industry = 'Technology'")

# Find by field
tech_accounts = q.find_by_field("Account", "Industry", "Technology",
                                 select_fields=["Id", "Name", "Phone"])

# Search across objects (SOSL)
search_results = q.sosl("FIND {Acme} IN ALL FIELDS RETURNING Account(Name), Contact(Name)")
```
