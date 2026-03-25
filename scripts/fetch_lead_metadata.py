"""
Fetch Lead Object Metadata and Save as Knowledge
═══════════════════════════════════════════════════
Connects to your Salesforce org, describes the Lead object,
and saves all field metadata as a markdown reference file
that gets auto-loaded into the AI's knowledge base.

Usage:
    python scripts/fetch_lead_metadata.py

This generates:
    salesforce/resources/lead_field_reference.md
    .agents/skills/salesforce-schema/references/lead_metadata.md
"""

import os
import sys
from datetime import datetime

# Add paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "salesforce", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from sf_auth import SalesforceAuth
from sf_query import SalesforceQuery


def fetch_and_save_lead_metadata():
    """Fetch Lead metadata from the live org and save as reference files."""

    # Authenticate
    auth = SalesforceAuth(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
    )
    auth.authenticate_simple()
    query = SalesforceQuery(auth)

    # Describe the Lead object
    print("Fetching Lead object metadata...")
    fields = query.describe_fields("Lead")

    # Categorize fields
    standard_fields = [f for f in fields if not f["name"].endswith("__c")]
    custom_fields = [f for f in fields if f["name"].endswith("__c")]

    # Build the markdown content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"""# Lead Object — Field Reference

> Auto-generated from live Salesforce org on {timestamp}
> Total fields: {len(fields)} ({len(standard_fields)} standard, {len(custom_fields)} custom)

## Standard Fields ({len(standard_fields)})

| API Name | Label | Type |
|----------|-------|------|
"""
    for f in sorted(standard_fields, key=lambda x: x["name"]):
        md += f"| `{f['name']}` | {f['label']} | {f['type']} |\n"

    if custom_fields:
        md += f"""
## Custom Fields ({len(custom_fields)})

| API Name | Label | Type |
|----------|-------|------|
"""
        for f in sorted(custom_fields, key=lambda x: x["name"]):
            md += f"| `{f['name']}` | {f['label']} | {f['type']} |\n"

    # Key fields for common operations
    md += """
## Key Fields for Common Operations

### Lead Creation (Required/Important Fields)
| Field | API Name | Required |
|-------|----------|----------|
| Last Name | `LastName` | ✅ Yes |
| Company | `Company` | ✅ Yes |
| First Name | `FirstName` | No |
| Email | `Email` | No |
| Phone | `Phone` | No |
| Status | `Status` | ✅ Yes (default: Open) |
| Lead Source | `LeadSource` | No |
| Title | `Title` | No |
| Industry | `Industry` | No |

### Lead Conversion Fields
| Field | API Name | Description |
|-------|----------|-------------|
| Is Converted | `IsConverted` | Whether the lead has been converted |
| Converted Date | `ConvertedDate` | Date of conversion |
| Converted Account | `ConvertedAccountId` | Account created from conversion |
| Converted Contact | `ConvertedContactId` | Contact created from conversion |
| Converted Opportunity | `ConvertedOpportunityId` | Opportunity created from conversion |

### Address Fields
| Field | API Name |
|-------|----------|
| Street | `Street` |
| City | `City` |
| State | `State` |
| Postal Code | `PostalCode` |
| Country | `Country` |

### Useful Filter Fields
| Field | API Name | Type | Use For |
|-------|----------|------|---------|
| Status | `Status` | picklist | Lead pipeline |
| Lead Source | `LeadSource` | picklist | Source analytics |
| Industry | `Industry` | picklist | Industry breakdown |
| Rating | `Rating` | picklist | Lead quality |
| Created Date | `CreatedDate` | datetime | Time-based reporting |
| Owner | `OwnerId` | reference | Assignment tracking |
"""

    # Save to salesforce/resources (loaded into knowledge base)
    resources_path = os.path.join(BASE_DIR, "salesforce", "resources", "lead_field_reference.md")
    os.makedirs(os.path.dirname(resources_path), exist_ok=True)
    with open(resources_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ Saved to: {resources_path}")

    # Also save to schema skill references
    schema_ref_path = os.path.join(BASE_DIR, ".agents", "skills", "salesforce-schema", "references", "lead_metadata.md")
    os.makedirs(os.path.dirname(schema_ref_path), exist_ok=True)
    with open(schema_ref_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ Saved to: {schema_ref_path}")

    print(f"\n📋 Lead has {len(fields)} fields ({len(standard_fields)} standard, {len(custom_fields)} custom)")
    print("🔄 Restart the agent to load the new metadata into the knowledge base.")


if __name__ == "__main__":
    fetch_and_save_lead_metadata()
