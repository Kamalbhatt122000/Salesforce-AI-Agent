# Salesforce Files API Reference

## Object Model

### ContentVersion (File Version)

Represents a specific version of a file. This is where the actual file data is stored.

| Field | Type | Description |
|-------|------|-------------|
| `Id` | ID | ContentVersion ID (starts with `068`) |
| `ContentDocumentId` | Reference | Parent ContentDocument ID |
| `Title` | Text(255) | Display name of the file |
| `Description` | Text(255) | File description |
| `PathOnClient` | Text(500) | Original file path/name (includes extension) |
| `VersionData` | Base64 | The actual file content (base64-encoded) |
| `VersionNumber` | Text | Version number (e.g., "1", "2", "3") |
| `IsLatest` | Boolean | True if this is the latest version |
| `FileType` | Text | File type (PDF, DOCX, PNG, etc.) |
| `FileExtension` | Text | File extension without dot (pdf, docx, png) |
| `ContentSize` | Number | File size in bytes |
| `Checksum` | Text | MD5 checksum of the file |
| `CreatedDate` | DateTime | When the version was created |
| `CreatedById` | Reference | User who created this version |
| `ContentModifiedDate` | DateTime | When the file content was last modified |

**Key Points**:
- Use `VersionData` to upload/download file content
- `PathOnClient` must include the file extension
- `IsLatest = true` to get the current version
- Creating a ContentVersion automatically creates a ContentDocument

### ContentDocument (File Container)

Represents the file itself (metadata container). Multiple versions point to one document.

| Field | Type | Description |
|-------|------|-------------|
| `Id` | ID | ContentDocument ID (starts with `069`) |
| `Title` | Text(255) | Display name (without extension) |
| `FileType` | Text | File type (PDF, DOCX, PNG, etc.) |
| `FileExtension` | Text | File extension without dot |
| `ContentSize` | Number | Size of the latest version in bytes |
| `LatestPublishedVersionId` | Reference | ID of the latest ContentVersion |
| `ParentId` | Reference | Library or workspace ID (if applicable) |
| `OwnerId` | Reference | User who owns the file |
| `CreatedDate` | DateTime | When the document was created |
| `CreatedById` | Reference | User who created the document |
| `LastModifiedDate` | DateTime | When the document was last modified |
| `LastModifiedById` | Reference | User who last modified the document |

**Key Points**:
- Cannot be created directly — created automatically when you create a ContentVersion
- Deleting a ContentDocument deletes all versions and all links
- Use `LatestPublishedVersionId` to get the current version

### ContentDocumentLink (File-Record Link)

Links a ContentDocument to a record (Account, Lead, Contact, etc.).

| Field | Type | Description |
|-------|------|-------------|
| `Id` | ID | ContentDocumentLink ID (starts with `06A`) |
| `ContentDocumentId` | Reference | The file being linked |
| `LinkedEntityId` | Reference | The record the file is linked to |
| `ShareType` | Picklist | V (Viewer), C (Collaborator), I (Inferred) |
| `Visibility` | Picklist | AllUsers, InternalUsers, SharedUsers |

**ShareType Values**:
- `V` (Viewer): Read-only access
- `C` (Collaborator): Can edit and share the file
- `I` (Inferred): Access inherited from the linked record's permissions

**Key Points**:
- One file can have multiple links (shared across records)
- Deleting a link removes the file from that record only
- Deleting the ContentDocument deletes all links

## REST API Endpoints

### Upload a File

**Create ContentVersion**

```
POST /services/data/v62.0/sobjects/ContentVersion
Content-Type: application/json

{
  "Title": "Contract",
  "PathOnClient": "contract.pdf",
  "VersionData": "<base64-encoded-content>"
}
```

**Response**:
```json
{
  "id": "068...",
  "success": true,
  "errors": []
}
```

### Download a File

**Get VersionData (Binary Content)**

```
GET /services/data/v62.0/sobjects/ContentVersion/{id}/VersionData
Authorization: Bearer <access_token>
```

**Response**: Binary file content (not JSON)

### Link File to Record

**Create ContentDocumentLink**

```
POST /services/data/v62.0/sobjects/ContentDocumentLink
Content-Type: application/json

{
  "ContentDocumentId": "069...",
  "LinkedEntityId": "00Q...",
  "ShareType": "V"
}
```

### Delete a File

**Delete ContentDocument**

```
DELETE /services/data/v62.0/sobjects/ContentDocument/{id}
Authorization: Bearer <access_token>
```

**Response**: 204 No Content (success)

## SOQL Queries

### List Files on a Record

```sql
SELECT ContentDocument.Id,
       ContentDocument.Title,
       ContentDocument.FileType,
       ContentDocument.ContentSize,
       ContentDocument.CreatedDate,
       ContentDocument.LatestPublishedVersionId
FROM ContentDocumentLink
WHERE LinkedEntityId = '00Q...'
ORDER BY ContentDocument.CreatedDate DESC
```

### Get File Details

```sql
SELECT Id, Title, FileType, FileExtension, ContentSize,
       CreatedDate, CreatedBy.Name, LastModifiedDate,
       LatestPublishedVersionId, OwnerId, Owner.Name
FROM ContentDocument
WHERE Id = '069...'
```

### Get Latest Version of a File

```sql
SELECT Id, Title, VersionNumber, ContentSize, FileType,
       FileExtension, CreatedDate, IsLatest
FROM ContentVersion
WHERE ContentDocumentId = '069...'
AND IsLatest = true
```

### Find Files by Name

```sql
SELECT Id, Title, FileType, ContentSize, CreatedDate
FROM ContentDocument
WHERE Title LIKE '%contract%'
ORDER BY CreatedDate DESC
```

### Count Files on a Record

```sql
SELECT COUNT()
FROM ContentDocumentLink
WHERE LinkedEntityId = '00Q...'
```

### Get All Versions of a File

```sql
SELECT Id, VersionNumber, Title, ContentSize, CreatedDate, IsLatest
FROM ContentVersion
WHERE ContentDocumentId = '069...'
ORDER BY VersionNumber DESC
```

## File Size Limits

| Org Type | Max File Size |
|----------|---------------|
| Standard | 2 GB per file |
| Some orgs | 38 MB per file |
| Attachments (legacy) | 25 MB per file |

**Check your org's limit**:
```sql
SELECT MAX(ContentSize) FROM ContentDocument
```

## Supported File Types

| Category | Extensions |
|----------|------------|
| **Documents** | PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, RTF, ODT, ODS, ODP |
| **Images** | JPG, JPEG, PNG, GIF, BMP, SVG, TIFF |
| **Archives** | ZIP, RAR, 7Z, TAR, GZ |
| **Code/Data** | HTML, CSS, JS, JSON, XML, CSV, SQL |
| **Media** | MP4, MP3, AVI, MOV, WMV, WAV |
| **Other** | EML, MSG, ICS, VCF |

**Blocked file types** (for security):
- EXE, BAT, CMD, COM, SCR, VBS, JS (executable scripts)
- Check your org's security settings for the full list

## Base64 Encoding

Files must be base64-encoded before uploading to `VersionData`.

### Python Example

```python
import base64

# Read file
with open("document.pdf", "rb") as f:
    file_bytes = f.read()

# Encode to base64
file_base64 = base64.b64encode(file_bytes).decode("utf-8")

# Use in ContentVersion
content_version_data = {
    "Title": "Document",
    "PathOnClient": "document.pdf",
    "VersionData": file_base64
}
```

### JavaScript Example

```javascript
// Browser
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];

const reader = new FileReader();
reader.onload = function(e) {
    const base64 = e.target.result.split(',')[1]; // Remove data:... prefix
    // Use base64 in ContentVersion
};
reader.readAsDataURL(file);
```

## Error Codes

| Error | Cause | Solution |
|-------|-------|----------|
| `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY` | User lacks permissions | Grant "Create" on ContentVersion |
| `FILE_SIZE_LIMIT_EXCEEDED` | File too large | Compress or split file |
| `INVALID_TYPE` | Unsupported file type | Convert to supported format |
| `REQUIRED_FIELD_MISSING` | Missing Title or PathOnClient | Provide both fields |
| `ENTITY_IS_DELETED` | File or record deleted | Check Recycle Bin |
| `INVALID_CROSS_REFERENCE_KEY` | Invalid LinkedEntityId | Verify record ID exists |
| `DUPLICATE_VALUE` | File already linked to record | Check existing links first |

## Permissions Required

### To Upload Files
- Create permission on ContentVersion
- Create permission on ContentDocumentLink (to link to records)

### To Download Files
- Read permission on ContentVersion
- Read permission on ContentDocument

### To Delete Files
- Delete permission on ContentDocument
- Or: Own the file (OwnerId = current user)

### To Share Files
- Create permission on ContentDocumentLink
- Read permission on ContentDocument

## Best Practices

1. **Always set PathOnClient with extension**: `"contract.pdf"` not `"contract"`
2. **Use ContentDocument ID for deletion**: Not ContentVersion ID
3. **Check file size before upload**: Avoid exceeding org limits
4. **Use ShareType = "V" by default**: Viewer access is safest
5. **Query IsLatest = true**: To get the current version
6. **Handle large files**: Consider chunking for files > 38 MB
7. **Clean up old versions**: Delete old ContentVersions if not needed
8. **Use meaningful titles**: Helps with search and organization

## Versioning

When you upload a new version of an existing file:

1. Create a new ContentVersion with the same ContentDocumentId
2. The new version becomes IsLatest = true
3. Old versions remain accessible (IsLatest = false)
4. All ContentDocumentLinks remain intact

```python
# Upload new version
new_version_data = {
    "ContentDocumentId": "069...",  # Existing document
    "PathOnClient": "contract_v2.pdf",
    "VersionData": base64_content
}
```

## Migration from Attachments

To migrate from legacy Attachments to ContentVersion:

```sql
-- Query old attachments
SELECT Id, Name, Body, ParentId, ContentType
FROM Attachment
WHERE ParentId = '00Q...'
```

```python
# For each attachment:
# 1. Download Body (base64)
# 2. Create ContentVersion with VersionData = Body
# 3. Link to same ParentId using ContentDocumentLink
# 4. Delete old Attachment
```
