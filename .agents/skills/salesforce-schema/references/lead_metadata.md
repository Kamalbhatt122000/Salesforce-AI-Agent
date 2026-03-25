# Lead Object — Field Reference

> Auto-generated from live Salesforce org on 2026-03-20 15:57:18
> Total fields: 80 (65 standard, 15 custom)

## Standard Fields (65)

| API Name | Label | Type |
|----------|-------|------|
| `Address` | Address | address |
| `AnnualRevenue` | Annual Revenue | currency |
| `City` | City | string |
| `CleanStatus` | Clean Status | picklist |
| `Company` | Company | string |
| `CompanyDunsNumber` | Company D-U-N-S Number | string |
| `ConvertedAccountId` | Converted Account ID | reference |
| `ConvertedContactId` | Converted Contact ID | reference |
| `ConvertedDate` | Converted Date | date |
| `ConvertedOpportunityId` | Converted Opportunity ID | reference |
| `Country` | Country | string |
| `CountryCode` | Country Code | picklist |
| `CreatedById` | Created By ID | reference |
| `CreatedDate` | Created Date | datetime |
| `CurrencyIsoCode` | Lead Currency | picklist |
| `DandbCompanyId` | D&B Company ID | reference |
| `Description` | Description | textarea |
| `DoNotCall` | Do Not Call | boolean |
| `Email` | Email | email |
| `EmailBouncedDate` | Email Bounced Date | datetime |
| `EmailBouncedReason` | Email Bounced Reason | string |
| `Fax` | Fax | phone |
| `FirstName` | First Name | string |
| `GenderIdentity` | Gender Identity | picklist |
| `GeocodeAccuracy` | Geocode Accuracy | picklist |
| `HasOptedOutOfEmail` | Email Opt Out | boolean |
| `HasOptedOutOfFax` | Fax Opt Out | boolean |
| `Id` | Lead ID | id |
| `IndividualId` | Individual ID | reference |
| `Industry` | Industry | picklist |
| `IsConverted` | Converted | boolean |
| `IsDeleted` | Deleted | boolean |
| `IsPriorityRecord` | Important | boolean |
| `IsUnreadByOwner` | Unread By Owner | boolean |
| `Jigsaw` | Data.com Key | string |
| `JigsawContactId` | Jigsaw Contact ID | string |
| `LastActivityDate` | Last Activity | date |
| `LastModifiedById` | Last Modified By ID | reference |
| `LastModifiedDate` | Last Modified Date | datetime |
| `LastName` | Last Name | string |
| `LastReferencedDate` | Last Referenced Date | datetime |
| `LastTransferDate` | Last Transfer Date | date |
| `LastViewedDate` | Last Viewed Date | datetime |
| `Latitude` | Latitude | double |
| `LeadSource` | Lead Source | picklist |
| `Longitude` | Longitude | double |
| `MasterRecordId` | Master Record ID | reference |
| `MobilePhone` | Mobile Phone | phone |
| `Name` | Full Name | string |
| `NumberOfEmployees` | Employees | int |
| `OwnerId` | Owner ID | reference |
| `PartnerAccountId` | Partner Account ID | reference |
| `Phone` | Phone | phone |
| `PhotoUrl` | Photo URL | url |
| `PostalCode` | Zip/Postal Code | string |
| `Pronouns` | Pronouns | picklist |
| `Rating` | Rating | picklist |
| `Salutation` | Salutation | picklist |
| `State` | State/Province | string |
| `StateCode` | State/Province Code | picklist |
| `Status` | Status | picklist |
| `Street` | Street | textarea |
| `SystemModstamp` | System Modstamp | datetime |
| `Title` | Title | string |
| `Website` | Website | url |

## Custom Fields (15)

| API Name | Label | Type |
|----------|-------|------|
| `Company_Summary__c` | Company_Summary | textarea |
| `CurrentGenerators__c` | Current Generator(s) | string |
| `NumberofLocations__c` | Number of Locations | double |
| `Primary__c` | Primary | picklist |
| `ProductInterest__c` | Product Interest | picklist |
| `SICCode__c` | SIC Code | string |
| `Sales_Insight__c` | Sales Insight | textarea |
| `npe01__Preferred_Email__c` | Preferred Email | picklist |
| `npe01__Preferred_Phone__c` | Preferred Phone | picklist |
| `npsp__Batch__c` | Batch | reference |
| `npsp__CompanyCity__c` | Company City | string |
| `npsp__CompanyCountry__c` | Company Country | string |
| `npsp__CompanyPostalCode__c` | Company Zip/Postal Code | string |
| `npsp__CompanyState__c` | Company State/Province | string |
| `npsp__CompanyStreet__c` | Company Street | textarea |

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
