---
name: salesforce-query
description: Execute SOQL queries and SOSL searches on a live Salesforce org. Use when the user asks to retrieve, search, or view data from Salesforce — such as listing records, counting objects, filtering by conditions, aggregating data, or searching across multiple objects. Handles auto-pagination for large result sets.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: data-access
  tier: 1
  dependencies:
    - salesforce-auth
---

# Salesforce Query Skill

Execute SOQL and SOSL queries against a connected Salesforce org.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- Valid Salesforce org with API access

## Available Tools

| Tool | Purpose |
|------|---------|
| `run_soql_query` | Execute a SOQL query and return results |
| `run_sosl_search` | Execute a SOSL full-text search across objects |

## Required Workflow

**Follow these steps in order.**

### Step 1: Identify the Query Type

- **Structured data retrieval** → Use SOQL (`run_soql_query`)
- **Full-text keyword search across objects** → Use SOSL (`run_sosl_search`)

### Step 2: Build the Query

For SOQL:
```sql
SELECT field1, field2 FROM ObjectName WHERE condition LIMIT n
```

For SOSL:
```sql
FIND {keyword} IN ALL FIELDS RETURNING Object1(Field1, Field2), Object2(Field1)
```

### Step 3: Execute and Present

1. Call the appropriate tool
2. Present results in a **markdown table** with clean formatting
3. If a field value is null, display as "—" (dash)
4. Every row must have the same number of columns as the header

### Step 4: Handle Edge Cases

- **No results**: Suggest alternative queries or check field/object names
- **Too many results**: Add LIMIT or WHERE filters
- **Invalid fields**: Use `describe_object` from the `salesforce-schema` skill first

## Common Patterns

```sql
-- Count records
SELECT COUNT() FROM Lead WHERE Status = 'Open'

-- Aggregate
SELECT Status, COUNT(Id) FROM Lead GROUP BY Status

-- Relationship query
SELECT Name, Account.Name FROM Contact WHERE Account.Industry = 'Technology'

-- Date filtering
SELECT Id, Name FROM Opportunity WHERE CloseDate = THIS_QUARTER

-- Subquery
SELECT Name, (SELECT LastName FROM Contacts) FROM Account
```

## Tips

- Use `LIMIT` to avoid retrieving too many records
- Use `ORDER BY` for sorted results
- For aggregate queries (COUNT, SUM, AVG), always GROUP BY the non-aggregate field
- Date literals: `TODAY`, `YESTERDAY`, `THIS_WEEK`, `THIS_MONTH`, `THIS_QUARTER`, `THIS_YEAR`, `LAST_N_DAYS:n`

## Scripts

| Script | Purpose |
|--------|---------|
| [sf_query.py](scripts/sf_query.py) | SOQL/SOSL query execution with auto-pagination |

## References

| Document | Contents |
|----------|----------|
| [SOQL Reference](references/soql_reference.md) | Complete SOQL/SOSL syntax, operators, date literals, limits |
