# Salesforce File Attachment Patterns

Common workflows and patterns for managing files in Salesforce.

## Pattern 1: Upload and Attach to Record

**Use Case**: User wants to upload a file and attach it to a Lead, Account, or other record.

### Workflow

```python
from sf_files_client import SalesforceFilesClient

# 1. Upload file
result = files_client.upload_file(
    file_path="/path/to/contract.pdf",
    title="Sales Contract Q1 2024",
    record_id="00Q...",  # Lead ID
    description="Contract for Q1 sales"
)

# 2. Confirm
print(f"Uploaded: {result['Title']}")
print(f"ContentDocument ID: {result['ContentDocumentId']}")
print(f"ContentVersion ID: {result['ContentVersionId']}")

# 3. Verify by listing files
files = files_client.list_files(record_id="00Q...")
for f in files:
    print(f"  - {f['Title']} ({f['FileType']}, {f['ContentSize']} bytes)")
```

### SOQL Verification

```sql
SELECT ContentDocument.Title, ContentDocument.FileType
FROM ContentDocumentLink
WHERE LinkedEntityId = '00Q...'
```

---

## Pattern 2: Share File Across Multiple Records

**Use Case**: Upload a file once and share it with multiple records (e.g., same proposal for multiple leads).

### Workflow

```python
# 1. Upload to first record
result = files_client.upload_file(
    file_path="/path/to/proposal.pdf",
    title="Product Proposal",
    record_id="00Q001..."  # First Lead
)

content_doc_id = result['ContentDocumentId']

# 2. Share with additional records
files_client.share_file_with_record(
    content_document_id=content_doc_id,
    record_id="00Q002...",  # Second Lead
    share_type="V"
)

files_client.share_file_with_record(
    content_document_id=content_doc_id,
    record_id="001...",  # Account
    share_type="V"
)

# 3. Verify links
query = f"""
    SELECT LinkedEntityId, LinkedEntity.Name
    FROM ContentDocumentLink
    WHERE ContentDocumentId = '{content_doc_id}'
"""
links = client.query(query)
print(f"File shared with {len(links)} records")
```

---

## Pattern 3: Download All Files from a Record

**Use Case**: Backup or export all files attached to a record.

### Workflow

```python
import os

# 1. List files
files = files_client.list_files(record_id="00Q...")

# 2. Create download directory
os.makedirs("downloads", exist_ok=True)

# 3. Download each file
for file in files:
    output_path = f"downloads/{file['Title']}.{file['FileExtension']}"
    files_client.download_file_to_disk(
        content_version_id=file['ContentVersionId'],
        output_path=output_path
    )
    print(f"Downloaded: {output_path}")
```

---

## Pattern 4: Replace a File (Upload New Version)

**Use Case**: Update an existing file with a new version.

### Workflow

```python
# 1. Find existing file
files = files_client.list_files(record_id="00Q...")
existing_file = next(f for f in files if f['Title'] == "Contract")

content_doc_id = existing_file['ContentDocumentId']

# 2. Upload new version
from sf_rest_client import SalesforceRESTClient

rest_client = SalesforceRESTClient(auth)

# Read new file
with open("/path/to/contract_v2.pdf", "rb") as f:
    file_bytes = f.read()

file_base64 = base64.b64encode(file_bytes).decode("utf-8")

# Create new ContentVersion with same ContentDocumentId
new_version_data = {
    "ContentDocumentId": content_doc_id,
    "PathOnClient": "contract_v2.pdf",
    "VersionData": file_base64,
    "ReasonForChange": "Updated terms"
}

version_id = rest_client.create("ContentVersion", new_version_data)
print(f"Uploaded new version: {version_id}")

# 3. Verify versions
query = f"""
    SELECT Id, VersionNumber, Title, CreatedDate, IsLatest
    FROM ContentVersion
    WHERE ContentDocumentId = '{content_doc_id}'
    ORDER BY VersionNumber DESC
"""
versions = rest_client.query(query)
for v in versions:
    latest = "✓" if v['IsLatest'] else ""
    print(f"  Version {v['VersionNumber']} {latest} - {v['CreatedDate']}")
```

---

## Pattern 5: Bulk Upload Files

**Use Case**: Upload multiple files to a record at once.

### Workflow

```python
import os
from pathlib import Path

# 1. Get all files from directory
file_dir = Path("/path/to/documents")
files_to_upload = list(file_dir.glob("*.pdf"))

# 2. Upload each file
record_id = "00Q..."
uploaded_files = []

for file_path in files_to_upload:
    try:
        result = files_client.upload_file(
            file_path=str(file_path),
            title=file_path.stem,  # Filename without extension
            record_id=record_id
        )
        uploaded_files.append(result)
        print(f"✅ {file_path.name}")
    except Exception as e:
        print(f"❌ {file_path.name}: {e}")

# 3. Summary
print(f"\nUploaded {len(uploaded_files)} of {len(files_to_upload)} files")
```

---

## Pattern 6: Delete Old Files

**Use Case**: Clean up old or outdated files from a record.

### Workflow

```python
from datetime import datetime, timedelta

# 1. List files
files = files_client.list_files(record_id="00Q...")

# 2. Filter files older than 90 days
cutoff_date = datetime.now() - timedelta(days=90)

old_files = [
    f for f in files
    if datetime.fromisoformat(f['CreatedDate'].replace('Z', '+00:00')) < cutoff_date
]

# 3. Delete old files
for file in old_files:
    confirm = input(f"Delete '{file['Title']}'? (y/n): ")
    if confirm.lower() == 'y':
        files_client.delete_file(file['ContentDocumentId'])
        print(f"Deleted: {file['Title']}")

print(f"Deleted {len(old_files)} old files")
```

---

## Pattern 7: Search Files by Name

**Use Case**: Find files across the org by title or keyword.

### Workflow

```python
# 1. Search using SOQL
search_term = "contract"

query = f"""
    SELECT Id, Title, FileType, ContentSize, CreatedDate, CreatedBy.Name
    FROM ContentDocument
    WHERE Title LIKE '%{search_term}%'
    ORDER BY CreatedDate DESC
    LIMIT 50
"""

results = rest_client.query(query)

# 2. Display results
print(f"Found {len(results)} files matching '{search_term}':\n")
for doc in results:
    size = files_client.format_file_size(doc['ContentSize'])
    print(f"  {doc['Title']} ({doc['FileType']}) - {size}")
    print(f"    Created: {doc['CreatedDate']} by {doc['CreatedBy']['Name']}")
    print(f"    ID: {doc['Id']}\n")
```

---

## Pattern 8: Upload from URL

**Use Case**: Download a file from a URL and upload it to Salesforce.

### Workflow

```python
import requests
import base64

# 1. Download file from URL
url = "https://example.com/document.pdf"
response = requests.get(url)

if response.status_code == 200:
    file_content = response.content
    
    # 2. Encode to base64
    file_base64 = base64.b64encode(file_content).decode("utf-8")
    
    # 3. Upload to Salesforce
    result = files_client.upload_file(
        file_content=file_base64,
        title="Downloaded Document",
        record_id="00Q...",
        description=f"Downloaded from {url}"
    )
    
    print(f"Uploaded: {result['Title']}")
else:
    print(f"Failed to download: {response.status_code}")
```

---

## Pattern 9: Generate and Upload Report

**Use Case**: Generate a report/document programmatically and upload it.

### Workflow

```python
import base64
from io import BytesIO

# 1. Generate content (example: CSV report)
csv_content = "Name,Email,Status\n"
csv_content += "John Doe,john@example.com,Active\n"
csv_content += "Jane Smith,jane@example.com,Active\n"

# 2. Convert to bytes and encode
csv_bytes = csv_content.encode("utf-8")
csv_base64 = base64.b64encode(csv_bytes).decode("utf-8")

# 3. Upload to Salesforce
result = files_client.upload_file(
    file_content=csv_base64,
    title="Lead Report",
    record_id="00Q...",
    description="Generated lead report"
)

print(f"Uploaded report: {result['Title']}")
```

---

## Pattern 10: Migrate from Legacy Attachments

**Use Case**: Convert old Attachment records to ContentVersion.

### Workflow

```python
# 1. Query legacy attachments
query = """
    SELECT Id, Name, Body, ParentId, ContentType, BodyLength
    FROM Attachment
    WHERE ParentId = '00Q...'
"""

attachments = rest_client.query(query)

# 2. Migrate each attachment
for att in attachments:
    try:
        # Body is already base64-encoded in Salesforce
        result = files_client.upload_file(
            file_content=att['Body'],
            title=att['Name'],
            record_id=att['ParentId'],
            description="Migrated from Attachment"
        )
        
        print(f"✅ Migrated: {att['Name']}")
        
        # 3. Delete old attachment (optional)
        # rest_client.delete("Attachment", att['Id'])
        
    except Exception as e:
        print(f"❌ Failed to migrate {att['Name']}: {e}")
```

---

## Pattern 11: Check File Permissions

**Use Case**: Verify who has access to a file.

### Workflow

```python
# 1. Get all links for a file
content_doc_id = "069..."

query = f"""
    SELECT Id, LinkedEntityId, LinkedEntity.Name, ShareType, Visibility
    FROM ContentDocumentLink
    WHERE ContentDocumentId = '{content_doc_id}'
"""

links = rest_client.query(query)

# 2. Display access
print(f"File shared with {len(links)} entities:\n")
for link in links:
    entity_name = link.get('LinkedEntity', {}).get('Name', 'Unknown')
    share_type = link['ShareType']
    
    access = {
        'V': 'Viewer (Read-only)',
        'C': 'Collaborator (Edit)',
        'I': 'Inferred (From record)'
    }.get(share_type, share_type)
    
    print(f"  {entity_name} - {access}")
```

---

## Pattern 12: Chunked Upload for Large Files

**Use Case**: Upload files larger than 38 MB using chunking.

### Workflow

```python
import base64
import math

def upload_large_file(file_path, title, record_id, chunk_size=35*1024*1024):
    """Upload large file in chunks (35 MB per chunk)."""
    
    file_path = Path(file_path)
    file_size = file_path.stat().st_size
    
    if file_size <= chunk_size:
        # Small file - upload normally
        return files_client.upload_file(file_path, title, record_id)
    
    # Large file - use chunking
    num_chunks = math.ceil(file_size / chunk_size)
    print(f"File size: {file_size} bytes, splitting into {num_chunks} chunks")
    
    # Note: Salesforce doesn't natively support chunked uploads
    # You would need to:
    # 1. Split file into chunks
    # 2. Upload each chunk as separate ContentVersion
    # 3. Use Apex or external service to reassemble
    
    # Alternative: Compress the file first
    import zipfile
    
    zip_path = f"{file_path}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_path, file_path.name)
    
    result = files_client.upload_file(zip_path, f"{title}.zip", record_id)
    os.remove(zip_path)
    
    return result
```

---

## Best Practices Summary

1. **Use ContentVersion, not Attachment**: Modern, versioned, shareable
2. **Always include file extension in PathOnClient**: Required for proper file type detection
3. **Use meaningful titles**: Helps with search and organization
4. **Set descriptions**: Provides context for the file
5. **Check file size before upload**: Avoid exceeding org limits
6. **Use ShareType = "V" by default**: Viewer access is safest
7. **Clean up old files regularly**: Manage storage limits
8. **Handle errors gracefully**: File uploads can fail for many reasons
9. **Verify uploads**: Always confirm the file was attached correctly
10. **Consider versioning**: Don't delete old versions if audit trail is needed

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `INSUFFICIENT_ACCESS` | Missing permissions | Grant "Create" on ContentVersion |
| `FILE_SIZE_LIMIT_EXCEEDED` | File too large | Compress or split file |
| `INVALID_TYPE` | Unsupported file type | Convert to supported format |
| `REQUIRED_FIELD_MISSING` | Missing Title or PathOnClient | Provide both fields |
| `INVALID_CROSS_REFERENCE_KEY` | Invalid record ID | Verify record exists |
| `DUPLICATE_VALUE` | File already linked | Check existing links first |
| `STRING_TOO_LONG` | Title > 255 chars | Truncate title |
| `MALFORMED_ID` | Invalid ID format | Check ID prefix and length |
