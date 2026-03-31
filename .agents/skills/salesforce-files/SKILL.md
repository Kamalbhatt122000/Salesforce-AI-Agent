---
name: salesforce-files
description: Manage files, attachments, and documents in Salesforce — upload files to records, download attachments, list files, delete files, and work with ContentVersion, ContentDocument, and Attachment objects. Use when the user asks to attach files to records, view attachments, download documents, manage Salesforce Files, or work with file libraries.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: data-integration
  tier: 2
  dependencies:
    - salesforce-auth
    - salesforce-crud
    - salesforce-query
---

# Salesforce Files & Attachments Skill

Manage files, attachments, and documents in Salesforce using ContentVersion, ContentDocument, and legacy Attachment APIs.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- User must have appropriate file permissions (Create, Read, Delete on ContentDocument)
- For legacy Attachments: permissions on the Attachment object

## Available Tools

| Tool | Purpose |
|------|---------|
| `upload_file` | Upload a file and attach it to a record (uses ContentVersion) |
| `list_files` | List all files attached to a specific record |
| `download_file` | Download a file by ContentDocument ID or ContentVersion ID |
| `delete_file` | Delete a file (ContentDocument) from Salesforce |
| `get_file_details` | Get metadata for a file (size, type, owner, dates) |
| `share_file_with_record` | Link an existing file to additional records |

## Salesforce File Storage Models

Salesforce has two file storage systems:

### 1. Salesforce Files (Modern — Recommended)

Uses three objects:
- **ContentDocument**: The file itself (metadata container)
- **ContentVersion**: Specific version of the file (stores the binary data)
- **ContentDocumentLink**: Links files to records (sharing)

**Advantages**:
- Version control (multiple versions of same file)
- Shareable across multiple records
- Better security and permissions
- Supports libraries and workspaces
- No 25 MB limit per file (up to 2 GB for most orgs)

### 2. Legacy Attachments (Old — Limited)

Uses one object:
- **Attachment**: File directly attached to a parent record

**Limitations**:
- No version control
- One file = one record (no sharing)
- 25 MB file size limit
- Deprecated for new implementations

**This skill focuses on Salesforce Files (ContentVersion/ContentDocument).**

## Required Workflow

### Uploading a File

**Follow these steps in order.**

#### Step 1: Prepare the File

- Get the file path or binary content
- Determine the file name and extension
- Identify the record ID to attach the file to (e.g., Lead, Account, Contact)

#### Step 2: Upload the File

Call `upload_file` with:
- `file_path` or `file_content` (base64-encoded)
- `title`: Display name for the file
- `record_id`: The record to attach the file to (optional — can share later)

The tool will:
1. Create a ContentVersion record with the file data
2. Automatically create a ContentDocument
3. Link the file to the specified record via ContentDocumentLink

#### Step 3: Confirm Upload

- Return the ContentDocument ID and ContentVersion ID
- Confirm the file name, size, and linked record
- Optionally query to verify the file is attached

### Listing Files on a Record

#### Step 1: Identify the Record

Get the record ID (e.g., Lead ID, Account ID)

#### Step 2: Query ContentDocumentLinks

Call `list_files` with the `record_id`

The tool will:
1. Query ContentDocumentLink WHERE LinkedEntityId = record_id
2. Join to ContentDocument and ContentVersion
3. Return file details: ID, Title, FileType, ContentSize, CreatedDate, Owner

#### Step 3: Present Results

Display files in a markdown table:

| File Name | Type | Size | Uploaded | Owner |
|-----------|------|------|----------|-------|
| Contract.pdf | PDF | 1.2 MB | 2024-01-15 | John Doe |
| Proposal.docx | DOCX | 456 KB | 2024-01-10 | Jane Smith |

### Downloading a File

#### Step 1: Get the File ID

Use `list_files` to get the ContentVersion ID or ContentDocument ID

#### Step 2: Download

Call `download_file` with the `content_version_id`

The tool will:
1. Query ContentVersion to get VersionData (the binary content)
2. Use the REST API endpoint: `/services/data/v62.0/sobjects/ContentVersion/{id}/VersionData`
3. Return the binary content and file metadata

#### Step 3: Save or Display

- Save to local file system
- Display file metadata (name, size, type)
- Confirm download success

### Deleting a File

#### Step 1: Identify the File

Get the ContentDocument ID (not ContentVersion ID)

#### Step 2: Delete

Call `delete_file` with the `content_document_id`

**IMPORTANT**: Deleting a ContentDocument deletes:
- All versions of the file
- All links to records (ContentDocumentLinks)
- The file is moved to the Recycle Bin (recoverable for 15 days)

#### Step 3: Confirm Deletion

Inform the user that the file and all its versions have been deleted

### Sharing a File with Multiple Records

#### Step 1: Upload Once

Upload the file using `upload_file` (attached to the first record)

#### Step 2: Share with Additional Records

Call `share_file_with_record` for each additional record:
- `content_document_id`: The file to share
- `record_id`: The record to link it to
- `share_type`: `V` (Viewer), `C` (Collaborator), or `I` (Inferred)

#### Step 3: Verify

Query ContentDocumentLink to confirm all links exist

## File Type Support

Salesforce supports these file types:

| Category | Extensions |
|----------|------------|
| **Documents** | PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, RTF |
| **Images** | JPG, JPEG, PNG, GIF, BMP, SVG |
| **Archives** | ZIP, RAR, 7Z, TAR, GZ |
| **Code** | HTML, CSS, JS, JSON, XML, CSV |
| **Other** | MP4, MP3, AVI, MOV (with limits) |

**File size limits**:
- Standard orgs: 2 GB per file
- Some orgs: 38 MB per file (check org limits)

## Common Queries

### List all files on a Lead
```sql
SELECT ContentDocument.Title, ContentDocument.FileType, 
       ContentDocument.ContentSize, ContentDocument.CreatedDate
FROM ContentDocumentLink
WHERE LinkedEntityId = '00Q...'
```

### Get file details
```sql
SELECT Id, Title, FileType, ContentSize, FileExtension, 
       CreatedDate, CreatedBy.Name, ContentModifiedDate
FROM ContentDocument
WHERE Id = '069...'
```

### Get latest version of a file
```sql
SELECT Id, Title, VersionNumber, ContentSize, FileType, 
       VersionData, CreatedDate
FROM ContentVersion
WHERE ContentDocumentId = '069...'
AND IsLatest = true
```

### Find files by name
```sql
SELECT Id, Title, FileType, ContentSize
FROM ContentDocument
WHERE Title LIKE '%contract%'
```

## ContentDocumentLink Share Types

| ShareType | Access Level | Use Case |
|-----------|--------------|----------|
| `V` | Viewer | Read-only access |
| `C` | Collaborator | Can edit and share |
| `I` | Inferred | Inherits from record permissions |

**Default**: Use `V` (Viewer) for most cases.

## Record ID Prefixes

Files can be attached to any record type:

| Prefix | Object |
|--------|--------|
| `001` | Account |
| `003` | Contact |
| `00Q` | Lead |
| `006` | Opportunity |
| `500` | Case |
| `a00` | Custom Object |

## Tips

- **Always use ContentVersion for uploads** — it's the modern, recommended approach
- **ContentDocument ID vs ContentVersion ID**: ContentDocument is the container, ContentVersion is the actual file version
- **Deleting is permanent after 15 days** — files go to Recycle Bin first
- **Large files**: For files > 38 MB, consider chunking or using Bulk API
- **File names**: Salesforce stores the title separately from the file extension
- **Permissions**: Users need "View All Data" or object-level permissions to see files
- **Libraries**: Files can also be stored in Content Libraries (not covered here)

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `INSUFFICIENT_ACCESS` | User lacks file permissions | Grant "Create" on ContentVersion |
| `FILE_SIZE_LIMIT_EXCEEDED` | File too large | Check org limits, compress file |
| `INVALID_TYPE` | Unsupported file type | Convert to supported format |
| `ENTITY_IS_DELETED` | Record or file deleted | Check Recycle Bin |
| `REQUIRED_FIELD_MISSING` | Missing Title or PathOnClient | Provide file name |

## Scripts

| Script | Purpose |
|--------|---------|
| [sf_files_client.py](scripts/sf_files_client.py) | Complete file management client — upload, download, list, delete, share |

## References

| Document | Contents |
|----------|----------|
| [File API Reference](references/file_api_reference.md) | ContentVersion/ContentDocument fields, REST endpoints, SOQL patterns |
| [Attachment Patterns](references/attachment_patterns.md) | Common workflows, base64 encoding, chunking, legacy Attachment migration |
| [File Permissions Guide](references/file_permissions.md) | Sharing rules, visibility, ContentDocumentLink configuration |

## Example Workflows

### Workflow 1: Upload a contract to a Lead

```python
# Upload file
content_doc_id = upload_file(
    file_path="/path/to/contract.pdf",
    title="Sales Contract",
    record_id="00Q..."
)

# Verify
files = list_files(record_id="00Q...")
# Shows: Sales Contract | PDF | 1.2 MB | ...
```

### Workflow 2: Share a file with multiple records

```python
# Upload to first record
content_doc_id = upload_file(
    file_path="/path/to/proposal.pdf",
    title="Proposal",
    record_id="00Q..."  # Lead
)

# Share with Account and Opportunity
share_file_with_record(content_doc_id, "001...", share_type="V")  # Account
share_file_with_record(content_doc_id, "006...", share_type="V")  # Opportunity
```

### Workflow 3: Download all files from a record

```python
# List files
files = list_files(record_id="00Q...")

# Download each
for file in files:
    content = download_file(file['ContentVersionId'])
    save_to_disk(content, file['Title'])
```

## Legacy Attachments (Reference Only)

If you must work with legacy Attachments:

### Upload Attachment
```python
attachment_id = create_record("Attachment", {
    "Name": "document.pdf",
    "Body": base64_encoded_content,
    "ParentId": "00Q..."
})
```

### Query Attachments
```sql
SELECT Id, Name, ContentType, BodyLength, CreatedDate
FROM Attachment
WHERE ParentId = '00Q...'
```

**Recommendation**: Migrate to ContentVersion/ContentDocument for new implementations.
