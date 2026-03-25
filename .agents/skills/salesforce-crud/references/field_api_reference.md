# CRUD Field API Reference

## Record ID Prefixes

| Prefix | Object |
|--------|--------|
| `001` | Account |
| `003` | Contact |
| `00Q` | Lead |
| `006` | Opportunity |
| `500` | Case |
| `00T` | Task |
| `00U` | Event |

## Common Field API Names by Object

### Lead

| Display Name | API Name | Type |
|-------------|----------|------|
| First Name | `FirstName` | Text |
| Last Name | `LastName` | Text (Required) |
| Company | `Company` | Text (Required) |
| Email | `Email` | Email |
| Phone | `Phone` | Phone |
| Mobile | `MobilePhone` | Phone |
| Title | `Title` | Text |
| Status | `Status` | Picklist |
| Lead Source | `LeadSource` | Picklist |
| Industry | `Industry` | Picklist |
| Rating | `Rating` | Picklist |
| Website | `Website` | URL |
| Street | `Street` | TextArea |
| City | `City` | Text |
| State | `State` | Text |
| Postal Code | `PostalCode` | Text |
| Country | `Country` | Text |
| Description | `Description` | TextArea |

### Contact

| Display Name | API Name | Type |
|-------------|----------|------|
| First Name | `FirstName` | Text |
| Last Name | `LastName` | Text (Required) |
| Email | `Email` | Email |
| Phone | `Phone` | Phone |
| Mobile | `MobilePhone` | Phone |
| Title | `Title` | Text |
| Account | `AccountId` | Reference |
| Mailing Street | `MailingStreet` | TextArea |
| Mailing City | `MailingCity` | Text |
| Mailing State | `MailingState` | Text |
| Mailing Zip | `MailingPostalCode` | Text |
| Mailing Country | `MailingCountry` | Text |
| Department | `Department` | Text |
| Birthdate | `Birthdate` | Date |

### Account

| Display Name | API Name | Type |
|-------------|----------|------|
| Account Name | `Name` | Text (Required) |
| Phone | `Phone` | Phone |
| Website | `Website` | URL |
| Industry | `Industry` | Picklist |
| Type | `Type` | Picklist |
| Annual Revenue | `AnnualRevenue` | Currency |
| Number of Employees | `NumberOfEmployees` | Number |
| Billing Street | `BillingStreet` | TextArea |
| Billing City | `BillingCity` | Text |
| Billing State | `BillingState` | Text |
| Billing Zip | `BillingPostalCode` | Text |
| Billing Country | `BillingCountry` | Text |
| Description | `Description` | LongTextArea |

### Opportunity

| Display Name | API Name | Type |
|-------------|----------|------|
| Opportunity Name | `Name` | Text (Required) |
| Stage | `StageName` | Picklist (Required) |
| Close Date | `CloseDate` | Date (Required) |
| Amount | `Amount` | Currency |
| Account | `AccountId` | Reference |
| Probability | `Probability` | Percent |
| Type | `Type` | Picklist |
| Lead Source | `LeadSource` | Picklist |
| Next Step | `NextStep` | Text |
| Description | `Description` | LongTextArea |

### Case

| Display Name | API Name | Type |
|-------------|----------|------|
| Contact | `ContactId` | Reference |
| Account | `AccountId` | Reference |
| Status | `Status` | Picklist |
| Priority | `Priority` | Picklist |
| Origin | `Origin` | Picklist |
| Subject | `Subject` | Text |
| Description | `Description` | LongTextArea |
| Type | `Type` | Picklist |

## System Fields (Read-Only on All Objects)

| Field | API Name | Description |
|-------|----------|-------------|
| Record ID | `Id` | Unique 18-character identifier |
| Created Date | `CreatedDate` | Timestamp of creation |
| Created By | `CreatedById` | User who created the record |
| Last Modified Date | `LastModifiedDate` | Timestamp of last update |
| Last Modified By | `LastModifiedById` | User who last modified |
| Owner | `OwnerId` | User or queue that owns the record |
| Deleted | `IsDeleted` | True if in Recycle Bin |
