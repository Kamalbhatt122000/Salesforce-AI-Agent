# Skills Structure Guide

## Overview

The codebase uses a **modular skills architecture** where each Salesforce capability is organized as a self-contained skill. Skills are located in `.agents/skills/` and follow a consistent structure.

## Directory Structure

```
.agents/skills/
├── salesforce-auth/              # Authentication & connection
├── salesforce-crud/              # Create, Read, Update, Delete operations
├── salesforce-query/             # SOQL/SOSL queries
├── salesforce-schema/            # Object metadata & custom fields
├── salesforce-lead-management/   # Lead lifecycle management
├── salesforce-bulk/              # Bulk API for large datasets
├── salesforce-reports/           # Report browsing & execution
├── salesforce-files/             # File & attachment management
├── salesforce-analytics/         # Data visualization & charts
├── salesforce-automation/        # Flows & automation
├── salesforce-security/          # Permissions & sharing
└── salesforce-task-management/   # Task & event management
```

## Skill Structure

Each skill follows this standard structure:

```
skill-name/
├── SKILL.md                      # Main skill documentation
├── references/                   # Supporting documentation
│   ├── reference1.md
│   └── reference2.md
└── scripts/                      # Python implementation scripts
    └── script.py
```

## SKILL.md Format

Every `SKILL.md` file contains:

### 1. **Frontmatter (YAML)**
```yaml
---
name: skill-name
description: What the skill does and when to use it
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: foundation|data-access|crm-workflow|analytics|data-integration
  tier: 0-3                       # Dependency tier (0 = foundation)
  dependencies:                   # Required skills
    - salesforce-auth
    - salesforce-schema
---
```

### 2. **Main Sections**

- **Prerequisites**: Required setup, credentials, permissions
- **Available Tools**: List of functions/operations provided
- **Required Workflow**: Step-by-step process to use the skill
- **Common Patterns**: Code examples and use cases
- **Tips**: Best practices and gotchas
- **Scripts**: Links to implementation files
- **References**: Links to detailed documentation

## Skill Categories & Tiers

### Categories
- **foundation** (tier 0): Core capabilities like authentication
- **data-access** (tier 1): CRUD, queries, schema operations
- **data-integration** (tier 2): Bulk operations, reports
- **crm-workflow** (tier 3): Business logic like lead management
- **analytics**: Reporting and visualization

### Tier System
- **Tier 0**: No dependencies (e.g., salesforce-auth)
- **Tier 1**: Depends on tier 0 (e.g., salesforce-crud, salesforce-query)
- **Tier 2**: Depends on tier 0-1 (e.g., salesforce-bulk, salesforce-reports)
- **Tier 3**: Depends on tier 0-2 (e.g., salesforce-lead-management)

## Key Skills Breakdown

### 1. salesforce-auth (Tier 0)
- **Purpose**: Authenticate to Salesforce
- **Methods**: Username-Password flow, OAuth 2.0
- **Scripts**: `sf_auth.py`
- **References**: `oauth_flows.md`

### 2. salesforce-crud (Tier 1)
- **Purpose**: Create, read, update, delete records
- **Tools**: `create_record`, `update_record`, `delete_record`, `get_record_all_fields`
- **Scripts**: `sf_rest_client.py`
- **Dependencies**: salesforce-auth, salesforce-schema

### 3. salesforce-query (Tier 1)
- **Purpose**: Execute SOQL/SOSL queries
- **Tools**: `run_soql_query`, `run_sosl_search`
- **Scripts**: `sf_query.py`
- **Dependencies**: salesforce-auth

### 4. salesforce-schema (Tier 1)
- **Purpose**: Manage object schemas and custom fields
- **Tools**: `describe_object`, `list_org_objects`, `create_custom_field`, `delete_custom_field`
- **References**: `supported_field_types.md`
- **Dependencies**: salesforce-auth

### 5. salesforce-lead-management (Tier 3)
- **Purpose**: Full lead lifecycle (create, update, convert)
- **Special**: Auto-converts leads when status = "Closed - Converted"
- **References**: `lead_field_reference.md`
- **Dependencies**: salesforce-auth, salesforce-crud, salesforce-query

### 6. salesforce-bulk (Tier 2)
- **Purpose**: Large-scale data operations (2000+ records)
- **API**: Bulk API 2.0
- **Scripts**: `sf_bulk_client.py`
- **References**: `bulk_api_reference.md`

### 7. salesforce-reports (Tier 2)
- **Purpose**: Browse, run, and visualize reports
- **Tools**: `list_reports`, `run_report`, `generate_chart`
- **References**: `report_api_reference.md`, `report_patterns.md`
- **Dependencies**: salesforce-auth, salesforce-analytics

### 8. salesforce-files (Tier 2)
- **Purpose**: Manage files, attachments, and documents
- **Tools**: `upload_file`, `download_file`, `list_files`, `delete_file`, `share_file_with_record`
- **Objects**: ContentVersion, ContentDocument, ContentDocumentLink
- **Scripts**: `sf_files_client.py`
- **References**: `file_api_reference.md`, `attachment_patterns.md`, `file_permissions.md`
- **Dependencies**: salesforce-auth, salesforce-crud, salesforce-query

## Reference Files

Reference files provide detailed technical documentation:

- **API references**: Endpoints, parameters, response formats
- **Field references**: Complete field API names and types
- **Pattern guides**: Common workflows and examples
- **Error codes**: Troubleshooting information

Example: `oauth_flows.md` contains:
- OAuth 2.0 flow comparison table
- SOAP login XML examples
- Environment variable setup
- Troubleshooting table

## Script Files

Python scripts implement the actual Salesforce API interactions:

- **sf_auth.py**: Authentication logic
- **sf_rest_client.py**: REST API client with CRUD operations
- **sf_query.py**: SOQL/SOSL execution
- **sf_bulk_client.py**: Bulk API 2.0 client
- **sf_reports_client.py**: Analytics API client
- **sf_files_client.py**: File and attachment management client

All scripts follow this pattern:
```python
class SalesforceClient:
    def __init__(self, auth):
        self.auth = auth
        self.base_url = f"{auth.instance_url}/services/data/v62.0"
    
    def _request(self, method, endpoint, data=None):
        # Generic API request handler
        pass
```

## Workflow Patterns

### Standard Workflow Structure
1. **Identify**: Determine what operation is needed
2. **Validate**: Check field names, permissions, prerequisites
3. **Execute**: Call the appropriate tool/function
4. **Confirm**: Verify the result and inform the user

### Example: Creating a Lead
1. Identify: User wants to create a lead
2. Validate: Ensure `LastName` and `Company` are provided
3. Execute: Call `create_record` with `object_name="Lead"`
4. Confirm: Query the created record and display it

## Best Practices

1. **Always use describe_object** before creating/updating if field names are uncertain
2. **Follow the tier system** - don't skip dependency skills
3. **Use bulk operations** for 2000+ records
4. **Validate field mappings** - never swap field values
5. **Present results in markdown tables** for readability
6. **Handle edge cases** - no results, too many results, invalid fields

## Integration Points

Skills integrate through:
- **Shared authentication**: All skills use `salesforce-auth`
- **Common scripts**: Scripts can be imported across skills
- **Dependency chain**: Higher-tier skills build on lower-tier ones
- **Consistent patterns**: All follow the same workflow structure

## Summary

The skills architecture provides:
- ✅ **Modularity**: Each capability is self-contained
- ✅ **Reusability**: Scripts and references are shared
- ✅ **Clarity**: Consistent structure across all skills
- ✅ **Scalability**: Easy to add new skills following the pattern
- ✅ **Documentation**: Every skill is fully documented with examples
