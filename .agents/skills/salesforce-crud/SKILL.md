---
name: salesforce-crud
description: Create, read, update, and delete records in a live Salesforce org. Use when the user asks to add a new record (contact, lead, account, opportunity, case, etc.), update an existing record's fields, or delete a record. Also handles fetching a single record with all its fields by ID.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: data-access
  tier: 1
  dependencies:
    - salesforce-auth
    - salesforce-schema
---

# Salesforce CRUD Skill

Perform Create, Read, Update, and Delete operations on Salesforce records.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- Knowledge of the target object's field API names (use `salesforce-schema` skill if unsure)

## Available Tools

| Tool | Purpose |
|------|---------|
| `create_record` | Create a new record on any object |
| `update_record` | Update fields on an existing record |
| `delete_record` | Delete a record by ID |
| `get_record_all_fields` | Fetch a single record with ALL fields (standard + custom) |

## Required Workflow

### Step 1: Identify the Operation

| User Intent | Tool to Use |
|-------------|-------------|
| "Create a lead", "Add a contact" | `create_record` |
| "Update the phone number", "Change the status" | `update_record` |
| "Delete this record", "Remove the account" | `delete_record` |
| "Show me all details for this lead", "What's the mobile number?" | `get_record_all_fields` |

### Step 2: Validate Field Mappings (for Create/Update)

**CRITICAL — Follow these rules exactly:**

1. Use `describe_object` (from `salesforce-schema` skill) if unsure of field API names
2. Map user-provided values to the **CORRECT** Salesforce field API names:
   - "Last Name" → `LastName`
   - "First Name" → `FirstName`
   - "Company" → `Company`
   - "Email" → `Email`
   - "Phone" → `Phone`
   - "Mobile" → `MobilePhone`
3. **NEVER swap field values.** Double-check before calling the tool.

### Step 3: Execute the Operation

- **Create**: Call `create_record` with `object_name` and `field_values`
- **Update**: Call `update_record` with `object_name`, `record_id`, and `field_values`
- **Delete**: Call `delete_record` with `object_name` and `record_id`
- **Read all fields**: Call `get_record_all_fields` with `object_name` and `record_id`

### Step 4: Confirm the Result

- After **creating** a record: Run a SOQL query (`run_soql_query`) to fetch it back by ID and show the saved values as confirmation
- After **updating**: Confirm the update and show what changed
- After **deleting**: Confirm the deletion
- After **reading**: Present the relevant field values the user asked for

## Record ID Prefixes

| Prefix | Object |
|--------|--------|
| `001` | Account |
| `003` | Contact |
| `00Q` | Lead |
| `006` | Opportunity |
| `500` | Case |
| `00T` | Task |
| `00U` | Event |

## Scripts

| Script | Purpose |
|--------|---------|
| [sf_rest_client.py](scripts/sf_rest_client.py) | REST API client for all CRUD operations, composite requests, and describe |

## References

| Document | Contents |
|----------|----------|
| [Field API Reference](references/field_api_reference.md) | Complete field API names for Lead, Contact, Account, Opportunity, Case |
