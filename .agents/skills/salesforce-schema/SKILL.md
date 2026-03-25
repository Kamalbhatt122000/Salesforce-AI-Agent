---
name: salesforce-schema
description: Manage Salesforce object schemas — describe objects to see all fields, create new custom fields, and delete custom fields. Use when the user asks about an object's structure, wants to add a new field to an object, remove a custom field, or needs to know what fields are available. Uses the Tooling API for custom field management.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: data-access
  tier: 1
  dependencies:
    - salesforce-auth
---

# Salesforce Schema Management Skill

Describe objects, create custom fields, and delete custom fields on any Salesforce object.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- System Administrator or Customize Application permission (for field create/delete)

## Available Tools

| Tool | Purpose |
|------|---------|
| `describe_object` | Get all field names, types, and labels for an object |
| `list_org_objects` | List all available objects in the org |
| `create_custom_field` | Create a new custom field on an object (via Tooling API) |
| `delete_custom_field` | Delete a custom field from an object (via Tooling API) |

## Required Workflow

### For Describing Objects

1. Call `describe_object` with the object API name (e.g., `Lead`, `Account`, `Contact`)
2. Present the fields in a readable table with Name, Type, and Label columns
3. Highlight key field types (required fields, picklists, relationships)

### For Creating Custom Fields

**Follow these steps in order. Do not skip steps.**

#### Step 1: Gather Requirements

Identify from the user:
- **Object name**: Which object to add the field to (e.g., `Lead`, `Account`)
- **Field label**: The display name (e.g., "Priority Score")
- **Field type**: One of the supported types (see references)
- **Optional**: length, precision, scale, picklist values, description, required

#### Step 2: Validate

- The field label will auto-generate the API name with `__c` suffix (e.g., "Priority Score" → `Priority_Score__c`)
- If creating a Picklist, ensure picklist values are provided
- If creating a Number/Currency/Percent, consider precision and scale

#### Step 3: Execute

Call `create_custom_field` with the validated parameters.

#### Step 4: Confirm

Report the success with:
- Field API name created
- Object it was added to
- Field type and configuration

### For Deleting Custom Fields

1. **Only custom fields** (ending in `__c`) can be deleted. Standard fields cannot be deleted.
2. Call `delete_custom_field` with the object name and field name
3. Confirm the deletion to the user

## Standard vs Custom Objects

- **Standard objects**: `Account`, `Contact`, `Lead`, `Opportunity`, `Case`, `Task`, `Event`
- **Custom objects**: End with `__c` (e.g., `Invoice__c`, `Project__c`)
- Custom fields on both standard and custom objects end with `__c`

## Tips

- Use `describe_object` before creating a field to ensure no duplicate exists
- Custom field names are unique per object — creating a duplicate will error
- After creating a field, it may take a moment to appear in the org's UI
- Deleted fields go to Salesforce's "Deleted Fields" section and can be restored within 15 days

## References

| Document | Contents |
|----------|----------|
| [Supported Field Types](references/supported_field_types.md) | All custom field types, precision/scale, naming conventions, Tooling API usage |
