---
name: salesforce-lead-management
description: Manage the full lead lifecycle in Salesforce — create leads, update lead status, convert leads to accounts and contacts. Use when the user mentions lead conversion, lead status changes, lead assignment, or the lead-to-opportunity pipeline. The system automatically converts leads when status is set to "Closed - Converted".
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: crm-workflow
  tier: 3
  dependencies:
    - salesforce-auth
    - salesforce-crud
    - salesforce-query
---

# Salesforce Lead Management Skill

Handle the complete lead lifecycle: creation, qualification, and conversion.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- Lead object must be available in the org

## Available Tools

| Tool | Purpose |
|------|---------|
| `create_record` | Create a new Lead |
| `update_record` | Update Lead fields (including status changes) |
| `get_record_all_fields` | Fetch complete Lead details by ID |
| `run_soql_query` | Query leads by criteria |

## Lead Lifecycle

```
New → Contacted → Qualified → Closed - Converted
                              Closed - Not Converted
```

## Required Workflow

### Creating a Lead

1. **Required fields**: `LastName`, `Company`
2. **Recommended fields**: `FirstName`, `Email`, `Phone`, `Title`, `LeadSource`, `Status`
3. Call `create_record` with `object_name = "Lead"`
4. Verify by querying the created record

### Updating Lead Status

1. Call `update_record` with the Lead ID and new `Status` value
2. Standard status values: `Open - Not Contacted`, `Working - Contacted`, `Closed - Converted`, `Closed - Not Converted`

### Automatic Lead Conversion

When a Lead's status is updated to **"Closed - Converted"**, the system AUTOMATICALLY:

1. Fetches the Lead's details (name, company, email, phone, address, etc.)
2. **Creates or finds an Account** matching the Lead's Company name
3. **Creates a Contact** linked to that Account with the Lead's personal info
4. Returns conversion details including the new Account ID and Contact ID

**After conversion, ALWAYS inform the user about:**
- The Account that was created or found (with ID and name)
- The Contact that was created (with ID and name)
- Whether the Account was newly created or already existed

### Querying Leads

Common lead queries:
```sql
-- All open leads
SELECT Id, Name, Company, Status, LeadSource FROM Lead WHERE IsConverted = false

-- Leads by source
SELECT LeadSource, COUNT(Id) FROM Lead GROUP BY LeadSource

-- Leads created this month
SELECT Id, Name, CreatedDate FROM Lead WHERE CreatedDate = THIS_MONTH

-- Specific lead by ID
SELECT Id, FirstName, LastName, Company, Email, Phone, MobilePhone, Status FROM Lead WHERE Id = '00Qxxxx'
```

## Tips

- Lead conversion is irreversible — once converted, the Lead cannot be "unconverted"
- If an Account with the same Company name already exists, the system links to it instead of creating a duplicate
- Use `get_record_all_fields` with `object_name = "Lead"` to fetch ALL fields for a lead when the user asks for specific data

## References

| Document | Contents |
|----------|----------|
| [Lead Field Reference](references/lead_field_reference.md) | All lead fields, status values, conversion mapping, common queries |
