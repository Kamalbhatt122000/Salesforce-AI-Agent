# Salesforce Files Skill - Architecture Diagram

## Skill Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                        TIER 0                                │
│                     Foundation                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                   salesforce-auth                            │
│              (Authentication & Connection)                   │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ depends on
                       │
        ┌──────────────┴──────────────┬──────────────────┐
        │                             │                  │
        ▼                             ▼                  ▼
┌───────────────┐            ┌───────────────┐   ┌──────────────┐
│   TIER 1      │            │   TIER 1      │   │   TIER 1     │
│ Data Access   │            │ Data Access   │   │ Data Access  │
├───────────────┤            ├───────────────┤   ├──────────────┤
│               │            │               │   │              │
│ salesforce-   │            │ salesforce-   │   │ salesforce-  │
│    crud       │            │    query      │   │   schema     │
│               │            │               │   │              │
└───────┬───────┘            └───────┬───────┘   └──────┬───────┘
        │                            │                  │
        │                            │                  │
        └────────────┬───────────────┴──────────────────┘
                     │
                     │ depends on
                     │
                     ▼
        ┌────────────────────────────┐
        │         TIER 2              │
        │    Data Integration         │
        ├────────────────────────────┤
        │                             │
        │    salesforce-files         │ ◄── NEW SKILL
        │  (File & Attachment Mgmt)   │
        │                             │
        └────────────────────────────┘
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    salesforce-files Skill                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   SKILL.md     │  │  README.md       │  │ example_usage  │ │
│  │                │  │                  │  │     .py        │ │
│  │ • Workflows    │  │ • Quick Start    │  │                │ │
│  │ • Tools        │  │ • Features       │  │ • Demo Code    │ │
│  │ • Patterns     │  │ • Use Cases      │  │ • Test Data    │ │
│  └────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              scripts/sf_files_client.py                   │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                           │  │
│  │  class SalesforceFilesClient:                            │  │
│  │    • upload_file()                                       │  │
│  │    • download_file()                                     │  │
│  │    • list_files()                                        │  │
│  │    • delete_file()                                       │  │
│  │    • share_file_with_record()                            │  │
│  │    • get_file_details()                                  │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    references/                            │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                           │  │
│  │  • file_api_reference.md                                 │  │
│  │    - Object model (ContentVersion, ContentDocument)      │  │
│  │    - REST endpoints                                      │  │
│  │    - SOQL queries                                        │  │
│  │                                                           │  │
│  │  • attachment_patterns.md                                │  │
│  │    - 12 common patterns                                  │  │
│  │    - Code examples                                       │  │
│  │                                                           │  │
│  │  • file_permissions.md                                   │  │
│  │    - Security model                                      │  │
│  │    - ShareType (V, C, I)                                 │  │
│  │    - Visibility settings                                 │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Salesforce Object Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    Salesforce File System                        │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐
    │  ContentDocument     │  ◄── File Container (metadata)
    │  ID: 069...          │
    ├──────────────────────┤
    │ • Title              │
    │ • FileType           │
    │ • ContentSize        │
    │ • OwnerId            │
    └──────────┬───────────┘
               │
               │ has many
               │
               ▼
    ┌──────────────────────┐
    │  ContentVersion      │  ◄── File Version (binary data)
    │  ID: 068...          │
    ├──────────────────────┤
    │ • VersionData        │      (base64 encoded file)
    │ • VersionNumber      │
    │ • IsLatest           │
    │ • PathOnClient       │
    └──────────────────────┘

               │
               │ linked via
               │
               ▼
    ┌──────────────────────┐
    │ ContentDocumentLink  │  ◄── File-to-Record Link
    │  ID: 06A...          │
    ├──────────────────────┤
    │ • ContentDocumentId  │
    │ • LinkedEntityId     │      (Lead, Account, etc.)
    │ • ShareType          │      (V, C, I)
    │ • Visibility         │
    └──────────────────────┘
               │
               │ links to
               │
               ▼
    ┌──────────────────────┐
    │   Any Record         │
    │   (Lead, Account,    │
    │    Contact, etc.)    │
    └──────────────────────┘
```

## Data Flow

### Upload Flow
```
┌─────────┐     ┌──────────────┐     ┌─────────────────┐
│  File   │────▶│ Base64       │────▶│ ContentVersion  │
│  (disk) │     │ Encode       │     │ (VersionData)   │
└─────────┘     └──────────────┘     └────────┬────────┘
                                               │
                                               │ auto-creates
                                               │
                                               ▼
                                    ┌──────────────────┐
                                    │ ContentDocument  │
                                    └────────┬─────────┘
                                             │
                                             │ link to record
                                             │
                                             ▼
                                    ┌──────────────────────┐
                                    │ ContentDocumentLink  │
                                    │ (to Lead/Account)    │
                                    └──────────────────────┘
```

### Download Flow
```
┌──────────────────┐     ┌──────────────┐     ┌─────────┐
│ ContentVersion   │────▶│ Base64       │────▶│  File   │
│ (VersionData)    │     │ Decode       │     │  (disk) │
└──────────────────┘     └──────────────┘     └─────────┘
```

### Share Flow
```
┌──────────────────┐
│ ContentDocument  │
│ (existing file)  │
└────────┬─────────┘
         │
         │ create link
         │
         ▼
┌──────────────────────┐     ┌──────────────────────┐
│ ContentDocumentLink  │────▶│ Record 1 (Lead)      │
│ ShareType: V         │     └──────────────────────┘
└──────────────────────┘
         │
         │ create link
         │
         ▼
┌──────────────────────┐     ┌──────────────────────┐
│ ContentDocumentLink  │────▶│ Record 2 (Account)   │
│ ShareType: V         │     └──────────────────────┘
└──────────────────────┘
```

## Integration with Other Skills

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill Ecosystem                           │
└─────────────────────────────────────────────────────────────┘

    salesforce-auth (Tier 0)
           │
           ├──▶ salesforce-crud (Tier 1)
           │         │
           │         └──▶ salesforce-lead-management (Tier 3)
           │                      │
           │                      │ uses files
           │                      │
           ├──▶ salesforce-query (Tier 1)    │
           │         │                        │
           │         │                        │
           └──▶ salesforce-files (Tier 2) ◄──┘
                     │
                     │ provides files to
                     │
                     ├──▶ salesforce-reports (Tier 2)
                     │    (export reports as files)
                     │
                     └──▶ salesforce-bulk (Tier 2)
                          (bulk file operations)
```

## API Endpoints Used

```
┌─────────────────────────────────────────────────────────────┐
│              Salesforce REST API v62.0                       │
└─────────────────────────────────────────────────────────────┘

POST   /sobjects/ContentVersion/
       └─▶ Upload file (create ContentVersion)

GET    /sobjects/ContentVersion/{id}/VersionData
       └─▶ Download file binary content

POST   /sobjects/ContentDocumentLink/
       └─▶ Link file to record (share)

DELETE /sobjects/ContentDocument/{id}
       └─▶ Delete file and all versions

GET    /query/?q=SELECT...FROM ContentDocumentLink...
       └─▶ List files on a record

GET    /query/?q=SELECT...FROM ContentDocument...
       └─▶ Get file metadata

GET    /query/?q=SELECT...FROM ContentVersion...
       └─▶ Get version details
```

## File Operations Summary

```
┌──────────────┬─────────────────┬──────────────────────────┐
│  Operation   │  Method         │  Salesforce Object       │
├──────────────┼─────────────────┼──────────────────────────┤
│  Upload      │  upload_file()  │  ContentVersion (POST)   │
│  Download    │  download_file()│  ContentVersion (GET)    │
│  List        │  list_files()   │  ContentDocumentLink (Q) │
│  Delete      │  delete_file()  │  ContentDocument (DEL)   │
│  Share       │  share_file()   │  ContentDocumentLink (P) │
│  Details     │  get_details()  │  ContentDocument (QUERY) │
└──────────────┴─────────────────┴──────────────────────────┘

Legend: (P) = POST, (Q) = QUERY, (DEL) = DELETE
```

## Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Permission Layers                         │
└─────────────────────────────────────────────────────────────┘

    Layer 1: Object Permissions
    ┌────────────────────────────────────┐
    │ Profile/Permission Set             │
    │ • Create on ContentVersion         │
    │ • Read on ContentVersion           │
    │ • Delete on ContentDocument        │
    └────────────────────────────────────┘
                    │
                    ▼
    Layer 2: Record Sharing
    ┌────────────────────────────────────┐
    │ ContentDocumentLink                │
    │ • ShareType: V, C, or I            │
    │ • Visibility: AllUsers/Internal    │
    └────────────────────────────────────┘
                    │
                    ▼
    Layer 3: Ownership
    ┌────────────────────────────────────┐
    │ ContentDocument.OwnerId            │
    │ • Owner has full control           │
    │ • Can transfer ownership           │
    └────────────────────────────────────┘
```

## Summary

The **salesforce-files** skill is fully integrated with:

✅ Consistent structure matching all existing skills
✅ Complete documentation (2,300+ lines)
✅ Production-ready Python client
✅ Comprehensive reference guides
✅ Working examples and patterns
✅ Security and permissions documentation
✅ Proper tier placement (Tier 2)
✅ Clear dependencies (auth, crud, query)
✅ Integration points with other skills
