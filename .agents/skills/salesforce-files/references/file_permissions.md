# Salesforce File Permissions Guide

Understanding and managing file access, sharing, and visibility in Salesforce.

## Permission Model Overview

Salesforce file permissions are controlled at multiple levels:

1. **Object-level permissions** (Profile/Permission Set)
2. **Record-level sharing** (ContentDocumentLink)
3. **Field-level security** (ContentVersion fields)
4. **Organization-wide defaults** (OWD)

## Object-Level Permissions

Users need these permissions to work with files:

### ContentVersion Permissions

| Permission | Allows User To |
|------------|----------------|
| **Read** | View file metadata and download files |
| **Create** | Upload new files and new versions |
| **Edit** | Modify file metadata (Title, Description) |
| **Delete** | Delete file versions (not the document) |

### ContentDocument Permissions

| Permission | Allows User To |
|------------|----------------|
| **Read** | View document metadata |
| **Create** | Not applicable (auto-created with ContentVersion) |
| **Edit** | Change document owner |
| **Delete** | Delete the entire document and all versions |

### ContentDocumentLink Permissions

| Permission | Allows User To |
|------------|----------------|
| **Read** | See which records a file is linked to |
| **Create** | Share files with records |
| **Edit** | Change sharing settings |
| **Delete** | Remove file links from records |

### Checking User Permissions

```sql
-- Check if user has ContentVersion permissions
SELECT SobjectType, PermissionsRead, PermissionsCreate, 
       PermissionsEdit, PermissionsDelete
FROM ObjectPermissions
WHERE ParentId IN (
    SELECT PermissionSetId 
    FROM PermissionSetAssignment 
    WHERE AssigneeId = '005...'
)
AND SobjectType = 'ContentVersion'
```

## ContentDocumentLink ShareType

When linking a file to a record, you specify the ShareType:

### ShareType Values

| Value | Name | Description | Use Case |
|-------|------|-------------|----------|
| `V` | **Viewer** | Read-only access to the file | Default for most cases |
| `C` | **Collaborator** | Can edit and reshare the file | Team collaboration |
| `I` | **Inferred** | Access inherited from record permissions | Dynamic access based on record |

### ShareType Examples

```python
# Viewer access (read-only)
files_client.share_file_with_record(
    content_document_id="069...",
    record_id="00Q...",
    share_type="V"
)

# Collaborator access (can edit)
files_client.share_file_with_record(
    content_document_id="069...",
    record_id="001...",
    share_type="C"
)

# Inferred access (from record)
files_client.share_file_with_record(
    content_document_id="069...",
    record_id="006...",
    share_type="I"
)
```

### When to Use Each ShareType

- **V (Viewer)**: 
  - Default choice
  - External stakeholders
  - Read-only documentation
  - Compliance files

- **C (Collaborator)**:
  - Team members working together
  - Files that need editing
  - Shared workspaces

- **I (Inferred)**:
  - When file access should match record access
  - Dynamic permission requirements
  - Role-based access

## Visibility Settings

ContentDocumentLink also has a Visibility field:

| Value | Description |
|-------|-------------|
| `AllUsers` | All users in the org can see the file |
| `InternalUsers` | Only internal users (not community/portal users) |
| `SharedUsers` | Only users with explicit access |

**Default**: `AllUsers` (most permissive)

### Setting Visibility

```python
# Create link with specific visibility
link_data = {
    "ContentDocumentId": "069...",
    "LinkedEntityId": "00Q...",
    "ShareType": "V",
    "Visibility": "InternalUsers"  # Restrict to internal users
}

rest_client.create("ContentDocumentLink", link_data)
```

## File Ownership

### Owner Permissions

The file owner (OwnerId on ContentDocument) has special privileges:

- Can always edit and delete the file
- Can change the owner
- Can modify all sharing settings
- Bypasses some permission checks

### Changing File Owner

```python
# Transfer ownership
rest_client.update("ContentDocument", "069...", {
    "OwnerId": "005..."  # New owner's User ID
})
```

### Query Files by Owner

```sql
SELECT Id, Title, Owner.Name, CreatedDate
FROM ContentDocument
WHERE OwnerId = '005...'
ORDER BY CreatedDate DESC
```

## Library Permissions

Files can be stored in Content Libraries with additional permission controls.

### Library Roles

| Role | Permissions |
|------|-------------|
| **Viewer** | View and download files |
| **Author** | Upload, edit, and delete own files |
| **Editor** | Edit and delete any file in library |
| **Owner** | Full control, manage library settings |

### Checking Library Access

```sql
SELECT Library.Name, Visibility, CanUpload, CanDownload
FROM ContentWorkspacePermission
WHERE UserId = '005...'
```

## Permission Scenarios

### Scenario 1: Public File (All Users)

```python
# Upload file
result = files_client.upload_file(
    file_path="public_doc.pdf",
    title="Public Document",
    record_id="001..."  # Account
)

# Link is automatically created with AllUsers visibility
# All org users can view this file
```

### Scenario 2: Restricted File (Specific Users)

```python
# Upload without linking to record
result = files_client.upload_file(
    file_path="confidential.pdf",
    title="Confidential Document"
    # No record_id = not linked to any record
)

content_doc_id = result['ContentDocumentId']

# Manually share with specific users/records
files_client.share_file_with_record(
    content_document_id=content_doc_id,
    record_id="005...",  # Specific User ID
    share_type="V"
)
```

### Scenario 3: Team Collaboration File

```python
# Upload to a record
result = files_client.upload_file(
    file_path="team_doc.docx",
    title="Team Document",
    record_id="006..."  # Opportunity
)

content_doc_id = result['ContentDocumentId']

# Share with team members as Collaborators
team_member_ids = ["005001...", "005002...", "005003..."]

for user_id in team_member_ids:
    files_client.share_file_with_record(
        content_document_id=content_doc_id,
        record_id=user_id,
        share_type="C"  # Collaborator access
    )
```

### Scenario 4: Inferred Access from Record

```python
# Upload to Lead
result = files_client.upload_file(
    file_path="lead_notes.pdf",
    title="Lead Notes",
    record_id="00Q..."
)

# Use Inferred sharing
# Users who can access the Lead can access the file
files_client.share_file_with_record(
    content_document_id=result['ContentDocumentId'],
    record_id="00Q...",
    share_type="I"  # Inferred from Lead permissions
)
```

## Checking File Access

### Who Can Access a File?

```sql
-- Get all users/records with access to a file
SELECT LinkedEntityId, LinkedEntity.Name, ShareType, Visibility
FROM ContentDocumentLink
WHERE ContentDocumentId = '069...'
```

### What Files Can a User Access?

```sql
-- Files accessible by a specific user
SELECT ContentDocument.Id, ContentDocument.Title, ShareType
FROM ContentDocumentLink
WHERE LinkedEntityId = '005...'  -- User ID
ORDER BY ContentDocument.CreatedDate DESC
```

### Files on Records User Owns

```sql
-- Files on Leads owned by user
SELECT ContentDocument.Title, LinkedEntityId
FROM ContentDocumentLink
WHERE LinkedEntityId IN (
    SELECT Id FROM Lead WHERE OwnerId = '005...'
)
```

## Security Best Practices

### 1. Principle of Least Privilege

- Default to `ShareType = "V"` (Viewer)
- Only grant Collaborator access when needed
- Use Inferred access for dynamic permissions

### 2. Audit File Access

```sql
-- Recent file access (requires Event Monitoring)
SELECT UserId, User.Name, ContentDocumentId, EventType, CreatedDate
FROM ContentDocumentLinkEvent
WHERE CreatedDate = LAST_N_DAYS:7
ORDER BY CreatedDate DESC
```

### 3. Regular Permission Reviews

```python
# List all Collaborator access
query = """
    SELECT ContentDocument.Title, LinkedEntity.Name, ShareType
    FROM ContentDocumentLink
    WHERE ShareType = 'C'
"""

collaborators = rest_client.query(query)
print(f"Files with Collaborator access: {len(collaborators)}")
```

### 4. Restrict Sensitive Files

```python
# Upload sensitive file with restricted visibility
link_data = {
    "ContentDocumentId": "069...",
    "LinkedEntityId": "00Q...",
    "ShareType": "V",
    "Visibility": "SharedUsers"  # Most restrictive
}
```

### 5. Monitor File Deletions

```sql
-- Files deleted in last 30 days (from Recycle Bin)
SELECT Name, DeletedDate, DeletedBy.Name
FROM ContentDocument
WHERE IsDeleted = true
AND DeletedDate = LAST_N_DAYS:30
ALL ROWS
```

## Common Permission Issues

### Issue 1: User Can't Upload Files

**Cause**: Missing Create permission on ContentVersion

**Solution**:
1. Go to Setup → Profiles/Permission Sets
2. Find user's profile
3. Enable "Create" on ContentVersion object

### Issue 2: User Can't See Files on Record

**Cause**: Missing ContentDocumentLink or wrong ShareType

**Solution**:
```python
# Check if link exists
query = f"""
    SELECT Id, ShareType
    FROM ContentDocumentLink
    WHERE ContentDocumentId = '069...'
    AND LinkedEntityId = '00Q...'
"""

links = rest_client.query(query)
if not links:
    # Create link
    files_client.share_file_with_record("069...", "00Q...", "V")
```

### Issue 3: User Can't Delete File

**Cause**: Not the owner and missing Delete permission

**Solution**:
- Transfer ownership to user, OR
- Grant Delete permission on ContentDocument

### Issue 4: External User Can't Access File

**Cause**: Visibility set to InternalUsers

**Solution**:
```python
# Update link visibility
rest_client.update("ContentDocumentLink", "06A...", {
    "Visibility": "AllUsers"
})
```

## Permission Hierarchy

File access is determined by this hierarchy (most to least restrictive):

1. **Object permissions** (must have Read on ContentVersion)
2. **ContentDocumentLink** (must have a link to the file)
3. **ShareType** (V, C, or I determines access level)
4. **Visibility** (SharedUsers, InternalUsers, or AllUsers)
5. **Record permissions** (if ShareType = I, inherits from record)

**A user needs to pass ALL levels to access a file.**

## API Permissions

When using API to manage files:

### Required Permissions
- API Enabled (on Profile)
- Read/Create on ContentVersion
- Read/Create on ContentDocumentLink

### OAuth Scopes
```
full
api
refresh_token
```

### Connected App Settings
- Enable OAuth
- Select appropriate scopes
- Set IP restrictions if needed

## Summary

| Task | Required Permission | ShareType | Visibility |
|------|---------------------|-----------|------------|
| Upload file | Create on ContentVersion | N/A | N/A |
| View file | Read on ContentVersion | V, C, or I | Any |
| Edit file metadata | Edit on ContentVersion | C | Any |
| Download file | Read on ContentVersion | V, C, or I | Any |
| Delete file | Delete on ContentDocument | Owner or C | Any |
| Share file | Create on ContentDocumentLink | C (to reshare) | Any |
| Change owner | Edit on ContentDocument | Owner only | Any |

**Default recommendation**: Use ShareType = "V" and Visibility = "AllUsers" for most cases.
