# Salesforce Files & Attachments Skill

Comprehensive file management for Salesforce using ContentVersion, ContentDocument, and ContentDocumentLink APIs.

## Quick Start

```python
from sf_auth import SalesforceAuth
from sf_files_client import SalesforceFilesClient

# Authenticate
auth = SalesforceAuth()
auth.authenticate_simple()

# Initialize client
files_client = SalesforceFilesClient(auth)

# Upload a file
result = files_client.upload_file(
    file_path="/path/to/document.pdf",
    title="Contract",
    record_id="00Q..."  # Lead ID
)

# List files on a record
files = files_client.list_files(record_id="00Q...")

# Download a file
content = files_client.download_file(content_version_id="068...")

# Delete a file
files_client.delete_file(content_document_id="069...")
```

## Features

- ✅ Upload files to any Salesforce record
- ✅ Download files with metadata
- ✅ List all files attached to a record
- ✅ Share files across multiple records
- ✅ Delete files and manage versions
- ✅ Support for all common file types (PDF, DOCX, images, etc.)
- ✅ Base64 encoding/decoding handled automatically
- ✅ File size formatting utilities

## Documentation

- **[SKILL.md](SKILL.md)** - Complete skill documentation with workflows
- **[file_api_reference.md](references/file_api_reference.md)** - API endpoints, SOQL queries, object model
- **[attachment_patterns.md](references/attachment_patterns.md)** - Common patterns and examples
- **[file_permissions.md](references/file_permissions.md)** - Security and sharing guide

## Scripts

- **[sf_files_client.py](scripts/sf_files_client.py)** - Main client implementation
- **[example_usage.py](example_usage.py)** - Complete working example

## Salesforce Objects

This skill works with three main objects:

1. **ContentVersion** - Stores the actual file data (binary content)
2. **ContentDocument** - Container for file metadata and versions
3. **ContentDocumentLink** - Links files to records (sharing)

## Common Use Cases

### Upload and Attach
```python
files_client.upload_file(
    file_path="contract.pdf",
    title="Sales Contract",
    record_id="00Q...",
    description="Q1 2024 contract"
)
```

### Share Across Records
```python
# Upload once
result = files_client.upload_file(file_path="proposal.pdf", title="Proposal")

# Share with multiple records
files_client.share_file_with_record(result['ContentDocumentId'], "00Q001...", "V")
files_client.share_file_with_record(result['ContentDocumentId'], "001...", "V")
```

### Download All Files
```python
files = files_client.list_files(record_id="00Q...")
for file in files:
    files_client.download_file_to_disk(
        content_version_id=file['ContentVersionId'],
        output_path=f"downloads/{file['Title']}.{file['FileExtension']}"
    )
```

## File Size Limits

- Standard orgs: **2 GB per file**
- Some orgs: **38 MB per file**
- Legacy Attachments: **25 MB per file** (deprecated)

## Supported File Types

Documents, images, archives, code files, media files, and more. See [file_api_reference.md](references/file_api_reference.md) for the complete list.

## Permissions Required

- **Create** on ContentVersion (to upload)
- **Read** on ContentVersion (to download)
- **Delete** on ContentDocument (to delete)
- **Create** on ContentDocumentLink (to share)

## ShareType Options

- `V` (Viewer) - Read-only access (default)
- `C` (Collaborator) - Can edit and reshare
- `I` (Inferred) - Inherits from record permissions

## Example Workflow

```python
# 1. Create a Lead
lead_id = rest_client.create("Lead", {
    "LastName": "Doe",
    "Company": "Acme Corp"
})

# 2. Upload contract
result = files_client.upload_file(
    file_path="contract.pdf",
    title="Sales Contract",
    record_id=lead_id
)

# 3. Verify upload
files = files_client.list_files(record_id=lead_id)
print(f"Files on Lead: {len(files)}")

# 4. Share with Account
files_client.share_file_with_record(
    content_document_id=result['ContentDocumentId'],
    record_id="001...",
    share_type="V"
)
```

## Running the Example

```bash
cd .agents/skills/salesforce-files
python example_usage.py
```

This will:
1. Create test Leads
2. Upload a sample file
3. List and download files
4. Share files across records
5. Clean up test data

## Integration with Other Skills

This skill depends on:
- **salesforce-auth** (Tier 0) - Authentication
- **salesforce-crud** (Tier 1) - Record operations
- **salesforce-query** (Tier 1) - SOQL queries

Works well with:
- **salesforce-lead-management** - Attach files to leads
- **salesforce-reports** - Export report data as files
- **salesforce-bulk** - Bulk file operations

## Best Practices

1. Use ContentVersion (modern) instead of Attachment (legacy)
2. Always include file extension in PathOnClient
3. Use meaningful titles for searchability
4. Default to ShareType = "V" (Viewer) for security
5. Check file size before upload
6. Handle errors gracefully (file size limits, permissions)
7. Clean up old files regularly

## Troubleshooting

| Error | Solution |
|-------|----------|
| `INSUFFICIENT_ACCESS` | Grant "Create" on ContentVersion |
| `FILE_SIZE_LIMIT_EXCEEDED` | Compress or split file |
| `INVALID_TYPE` | Convert to supported format |
| `REQUIRED_FIELD_MISSING` | Provide Title and PathOnClient |

## Migration from Legacy Attachments

See [attachment_patterns.md](references/attachment_patterns.md) for migration guide from old Attachment objects to ContentVersion.

## Version

- **Version**: 2.0
- **Category**: data-integration
- **Tier**: 2
- **API Version**: v62.0

## License

Part of the Salesforce Skills Architecture.
