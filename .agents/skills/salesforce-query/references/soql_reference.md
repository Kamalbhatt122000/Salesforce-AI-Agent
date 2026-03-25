# SOQL & SOSL Quick Reference

## SOQL Syntax

```sql
SELECT field1, field2 FROM ObjectName [WHERE condition] [ORDER BY field] [LIMIT n]
```

## Operators

| Operator | Example |
|----------|---------|
| `=`, `!=` | `Status = 'Open'` |
| `<`, `>`, `<=`, `>=` | `Amount > 10000` |
| `LIKE` | `Name LIKE 'Acme%'` |
| `IN` | `Status IN ('Open', 'Working')` |
| `NOT IN` | `Industry NOT IN ('Tech')` |
| `AND`, `OR` | `Status = 'Open' AND Amount > 5000` |
| `INCLUDES`, `EXCLUDES` | For multi-select picklists |

## Aggregate Functions

| Function | Description | Example |
|----------|-------------|---------|
| `COUNT()` | Count all records | `SELECT COUNT() FROM Lead` |
| `COUNT(field)` | Count non-null values | `SELECT COUNT(Email) FROM Contact` |
| `SUM(field)` | Sum numeric field | `SELECT SUM(Amount) FROM Opportunity` |
| `AVG(field)` | Average value | `SELECT AVG(Amount) FROM Opportunity` |
| `MIN(field)` | Minimum value | `SELECT MIN(CreatedDate) FROM Lead` |
| `MAX(field)` | Maximum value | `SELECT MAX(Amount) FROM Opportunity` |

## Date Literals

| Literal | Meaning |
|---------|---------|
| `TODAY` | Current day |
| `YESTERDAY` | Previous day |
| `TOMORROW` | Next day |
| `THIS_WEEK` | Current week (Sun–Sat) |
| `LAST_WEEK` | Previous full week |
| `THIS_MONTH` | Current calendar month |
| `LAST_MONTH` | Previous calendar month |
| `THIS_QUARTER` | Current fiscal quarter |
| `THIS_YEAR` | Current fiscal year |
| `LAST_N_DAYS:n` | Last n days from today |
| `NEXT_N_DAYS:n` | Next n days from today |
| `LAST_N_MONTHS:n` | Last n months |
| `LAST_N_YEARS:n` | Last n years |

## Relationship Queries

```sql
-- Parent-to-child (subquery)
SELECT Name, (SELECT LastName FROM Contacts) FROM Account

-- Child-to-parent (dot notation)
SELECT Name, Account.Name, Account.Industry FROM Contact
```

## Common Patterns

```sql
-- Count records
SELECT COUNT() FROM Lead WHERE Status = 'Open'

-- Group by with aggregate
SELECT Status, COUNT(Id) cnt FROM Lead GROUP BY Status

-- Relationship query
SELECT Name, Account.Name FROM Contact WHERE Account.Industry = 'Technology'

-- Date filtering
SELECT Id, Name FROM Opportunity WHERE CloseDate = THIS_QUARTER

-- Subquery
SELECT Name, (SELECT LastName FROM Contacts) FROM Account

-- HAVING clause (filter on aggregate)
SELECT LeadSource, COUNT(Id) FROM Lead GROUP BY LeadSource HAVING COUNT(Id) > 5

-- Nested condition
SELECT Id, Name FROM Account WHERE (Industry = 'Tech' OR Industry = 'Finance') AND AnnualRevenue > 1000000

-- ORDER BY with NULLS
SELECT Name, Email FROM Contact ORDER BY Email NULLS LAST LIMIT 20
```

## SOSL Syntax

```sql
FIND {searchTerm} IN ALL FIELDS RETURNING Object1(Field1, Field2), Object2(Field1)
```

### SOSL Search Scopes

| Scope | Searches In |
|-------|------------|
| `ALL FIELDS` | All searchable fields |
| `NAME FIELDS` | Name fields only |
| `EMAIL FIELDS` | Email fields only |
| `PHONE FIELDS` | Phone fields only |
| `SIDEBAR FIELDS` | Sidebar search fields |

### SOSL Examples

```sql
-- Basic search
FIND {Acme} IN ALL FIELDS RETURNING Account(Name, Industry), Contact(Name, Email)

-- Search in email fields
FIND {john@example.com} IN EMAIL FIELDS RETURNING Contact(Name, Email, Phone)

-- Search with wildcard
FIND {Acme*} IN NAME FIELDS RETURNING Account(Name)

-- Search with WHERE filter
FIND {Cloud} RETURNING Opportunity(Name, Amount WHERE Amount > 50000)
```

## Query Limits

| Limit | Value |
|-------|-------|
| Max SOQL length | 100,000 characters |
| Max records per query | 50,000 |
| Max SOQL queries per transaction | 100 |
| Max SOSL queries per transaction | 20 |
| Max relationship depth | 5 levels |
| Max subqueries | 20 per query |
