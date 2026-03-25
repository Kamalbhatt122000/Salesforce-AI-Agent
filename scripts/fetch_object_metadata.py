"""
Fetch Any Object Metadata and Save as Knowledge
════════════════════════════════════════════════
Connects to your Salesforce org, describes any object,
and saves all field metadata as a markdown reference file
that gets auto-loaded into the AI's knowledge base.

Usage:
    python scripts/fetch_object_metadata.py Lead
    python scripts/fetch_object_metadata.py Account
    python scripts/fetch_object_metadata.py Contact
    python scripts/fetch_object_metadata.py Opportunity
    python scripts/fetch_object_metadata.py Case
    python scripts/fetch_object_metadata.py --all    (fetches all common objects)

Generated files are placed in:
    salesforce/resources/<object>_field_reference.md
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

# Common Salesforce objects
COMMON_OBJECTS = ["Lead", "Account", "Contact", "Opportunity", "Case"]


def fetch_object_metadata(query, object_name):
    """Fetch object metadata and return as markdown string."""

    print(f"  Fetching {object_name} metadata...")
    fields = query.describe_fields(object_name)

    standard_fields = [f for f in fields if not f["name"].endswith("__c")]
    custom_fields = [f for f in fields if f["name"].endswith("__c")]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"""# {object_name} Object — Field Reference

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

    return md, len(fields), len(standard_fields), len(custom_fields)


def save_metadata(object_name, md_content):
    """Save metadata to resource files."""
    filename = f"{object_name.lower()}_field_reference.md"

    # Save to salesforce/resources (auto-loaded into knowledge base)
    resources_path = os.path.join(BASE_DIR, "salesforce", "resources", filename)
    os.makedirs(os.path.dirname(resources_path), exist_ok=True)
    with open(resources_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"  ✅ Saved: {resources_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/fetch_object_metadata.py Lead")
        print("  python scripts/fetch_object_metadata.py --all")
        print(f"\nCommon objects: {', '.join(COMMON_OBJECTS)}")
        sys.exit(1)

    # Authenticate
    auth = SalesforceAuth(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
    )
    auth.authenticate_simple()
    query = SalesforceQuery(auth)

    # Determine which objects to fetch
    if sys.argv[1] == "--all":
        objects = COMMON_OBJECTS
    else:
        objects = sys.argv[1:]

    print(f"\n📋 Fetching metadata for: {', '.join(objects)}\n")

    for obj in objects:
        try:
            md, total, std, custom = fetch_object_metadata(query, obj)
            save_metadata(obj, md)
            print(f"  📋 {obj}: {total} fields ({std} standard, {custom} custom)\n")
        except Exception as e:
            print(f"  ❌ Error fetching {obj}: {e}\n")

    print("🔄 Restart the agent to load the new metadata into the knowledge base.")


if __name__ == "__main__":
    main()
