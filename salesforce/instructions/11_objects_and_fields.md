# Objects & Fields — Salesforce

## Overview

Everything in Salesforce is organized around **objects** (similar to database tables). Objects contain **fields** (columns) and **records** (rows). There are standard objects (built-in) and custom objects (user-created).

## Standard Objects

### Core CRM Objects

| Object | API Name | Description |
|--------|----------|-------------|
| **Account** | `Account` | Companies and organizations |
| **Contact** | `Contact` | People associated with accounts |
| **Lead** | `Lead` | Potential customers (pre-conversion) |
| **Opportunity** | `Opportunity` | Sales deals and revenue tracking |
| **Case** | `Case` | Customer support issues |
| **Task** | `Task` | To-do items and activities |
| **Event** | `Event` | Calendar events and meetings |
| **Campaign** | `Campaign` | Marketing campaigns |
| **Product2** | `Product2` | Products in the catalog |
| **Pricebook2** | `Pricebook2` | Price lists |
| **PricebookEntry** | `PricebookEntry` | Product prices in a pricebook |
| **OpportunityLineItem** | `OpportunityLineItem` | Products on an opportunity |
| **CampaignMember** | `CampaignMember` | Members of a campaign |
| **User** | `User` | Salesforce users |
| **Group** | `Group` | Public groups and queues |

### Support Objects

| Object | API Name | Description |
|--------|----------|-------------|
| **CaseComment** | `CaseComment` | Comments on cases |
| **Solution** | `Solution` | Knowledge articles (classic) |
| **Knowledge__kav** | `Knowledge__kav` | Lightning Knowledge articles |
| **FeedItem** | `FeedItem` | Chatter feed posts |

---

## Custom Objects

Custom objects have a `__c` suffix:
- API Name: `Invoice__c`
- Lookup: `SELECT Id, Name FROM Invoice__c`

### Creating Custom Objects
**Setup → Object Manager → Create → Custom Object**

Key settings:
- **Label** and **Plural Label**
- **API Name** (auto-generated with `__c`)
- **Record Name** field (auto-number or text)
- **Allow Reports**, **Allow Activities**, **Track Field History**

---

## Field Types

| Type | Description | Example |
|------|-------------|---------|
| **Text** | Single-line string (max 255 chars) | `FirstName` |
| **Text Area** | Multi-line text | `Description` |
| **Text Area (Long)** | Up to 131,072 chars | `Notes__c` |
| **Text Area (Rich)** | HTML-formatted text | `Bio__c` |
| **Number** | Integer or decimal | `AnnualRevenue` |
| **Currency** | Money values | `Amount` |
| **Percent** | Percentage values | `Probability` |
| **Date** | Date only | `CloseDate` |
| **Date/Time** | Date + time | `CreatedDate` |
| **Checkbox** | Boolean (true/false) | `IsActive` |
| **Picklist** | Single-select dropdown | `Industry` |
| **Multi-Select Picklist** | Multi-select | `Languages__c` |
| **Email** | Email address | `Email` |
| **Phone** | Phone number | `Phone` |
| **URL** | Web address | `Website` |
| **Lookup** | Reference to another record | `AccountId` |
| **Master-Detail** | Strong parent-child relationship | `OpportunityId` |
| **Formula** | Calculated field | `DaysSinceCreated__c` |
| **Roll-Up Summary** | Aggregate child records | `TotalAmount__c` |
| **Auto Number** | Auto-incrementing ID | `Invoice_Number__c` |
| **External ID** | Field for external system keys | `ERP_Id__c` |

---

## Relationships

### Lookup Relationship
- Loosely couples two objects
- Child record can exist without parent
- No cascade delete (configurable)
- No roll-up summary fields

```
Contact.AccountId → Account (Lookup)
```

### Master-Detail Relationship
- Tightly couples parent and child
- Child cannot exist without parent
- Cascade delete (parent deleted → children deleted)
- Supports roll-up summary fields
- Child inherits parent's sharing/security

```
OpportunityLineItem.OpportunityId → Opportunity (Master-Detail)
```

### Many-to-Many (Junction Object)
Create a custom object with **two Master-Detail** relationships:

```
Account ← AccountContactRole → Contact
```

### Self-Relationship
An object referencing itself:
```
Account.ParentId → Account (Lookup to self)
```

### Polymorphic Relationship
A field that can reference multiple object types:
```
Task.WhoId → Contact OR Lead
Task.WhatId → Account OR Opportunity OR Case OR ...
```

---

## System Fields (Auto-populated)

| Field | Description |
|-------|-------------|
| `Id` | Unique 18-character record identifier |
| `CreatedDate` | When the record was created |
| `CreatedById` | User who created the record |
| `LastModifiedDate` | When the record was last modified |
| `LastModifiedById` | User who last modified it |
| `SystemModstamp` | System modification timestamp |
| `IsDeleted` | Whether in recycle bin |
| `RecordTypeId` | Record type (if applicable) |
| `OwnerId` | Record owner (user or queue) |

---

## Describe an Object (API)

```http
GET /services/data/v62.0/sobjects/Account/describe/
```

Returns:
- All fields (`name`, `type`, `label`, `length`, `nillable`, etc.)
- Child relationships
- Record type info
- Picklist values
