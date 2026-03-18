# Salesforce Object Model — Cheatsheet

---

## Core Object Relationships

```
┌──────────────┐
│   Campaign    │
│ (Marketing)   │───── CampaignMember ─────┐
└──────────────┘                            │
                                            ▼
┌──────────────┐         ┌──────────────┐  ┌──────────────┐
│    Lead      │ ──────▶ │   Account    │  │   Contact    │
│ (Prospect)   │ convert │  (Company)   │◀─│   (Person)   │
└──────────────┘         └──────┬───────┘  └──────┬───────┘
                                │                  │
                    ┌───────────┼───────────┐      │
                    ▼           ▼           ▼      │
             ┌──────────┐ ┌──────────┐ ┌────────┐ │
             │   Case   │ │Opportunity│ │Contract│ │
             │(Support) │ │  (Deal)   │ │        │ │
             └──────────┘ └─────┬─────┘ └────────┘ │
                                │                    │
                    ┌───────────┼───────────┐        │
                    ▼           ▼           ▼        │
            ┌────────────┐ ┌──────────┐ ┌────────┐  │
            │Opportunity │ │  Quote   │ │  Task  │◀─┘
            │ LineItem   │ │          │ │ Event  │
            │ (Product)  │ │          │ │(Activity)
            └─────┬──────┘ └──────────┘ └────────┘
                  │
            ┌─────▼──────┐
            │  Product2  │
            │  (Catalog) │──── PricebookEntry ──── Pricebook2
            └────────────┘
```

---

## Standard Objects Reference

### Sales Objects

| Object | API Name | Key Fields | Relationships |
|--------|----------|------------|---------------|
| **Lead** | `Lead` | FirstName, LastName, Company, Email, Status, Phone | → Account, Contact, Opportunity (via conversion) |
| **Account** | `Account` | Name, Industry, Phone, Website, AnnualRevenue, Type | Parent Account, → Contacts, Opportunities, Cases |
| **Contact** | `Contact` | FirstName, LastName, Email, Phone, Title, MailingAddress | → Account (lookup), → Opportunities (via OpportunityContactRole) |
| **Opportunity** | `Opportunity` | Name, Amount, StageName, CloseDate, Probability | → Account, → Contacts (via junction), → OpportunityLineItems |
| **OpportunityLineItem** | `OpportunityLineItem` | Quantity, UnitPrice, TotalPrice | → Opportunity (master-detail), → PricebookEntry |

### Product Objects

| Object | API Name | Key Fields | Relationships |
|--------|----------|------------|---------------|
| **Product** | `Product2` | Name, ProductCode, Description, IsActive, Family | → PricebookEntries |
| **Pricebook** | `Pricebook2` | Name, IsActive, IsStandard | → PricebookEntries |
| **Pricebook Entry** | `PricebookEntry` | UnitPrice, IsActive | → Product2, → Pricebook2 |

### Support Objects

| Object | API Name | Key Fields | Relationships |
|--------|----------|------------|---------------|
| **Case** | `Case` | Subject, Description, Status, Priority, Origin, Type | → Account, → Contact, → CaseComments |
| **Case Comment** | `CaseComment` | Body, IsPublished | → Case (master-detail) |

### Activity Objects

| Object | API Name | Key Fields | Relationships |
|--------|----------|------------|---------------|
| **Task** | `Task` | Subject, Status, Priority, ActivityDate, Description | WhoId → Contact/Lead, WhatId → Any object |
| **Event** | `Event` | Subject, StartDateTime, EndDateTime, Location | WhoId → Contact/Lead, WhatId → Any object |

### Marketing Objects

| Object | API Name | Key Fields | Relationships |
|--------|----------|------------|---------------|
| **Campaign** | `Campaign` | Name, Type, Status, StartDate, EndDate, BudgetedCost | → CampaignMembers |
| **Campaign Member** | `CampaignMember` | Status, LeadId, ContactId | → Campaign, → Lead or Contact |

### User & Setup

| Object | API Name | Key Fields |
|--------|----------|------------|
| **User** | `User` | Username, Email, FirstName, LastName, ProfileId, IsActive |
| **Profile** | `Profile` | Name |
| **UserRole** | `UserRole` | Name, ParentRoleId |
| **Group** | `Group` | Name, Type (Regular, Queue) |

---

## Custom Object Naming

| Element | Convention | Example |
|---------|------------|---------|
| Custom Object | `Object_Name__c` | `Invoice__c` |
| Custom Field | `Field_Name__c` | `Amount__c` |
| Custom Relationship | `Relationship_Name__r` | `Invoice__r` |
| Custom Metadata Type | `Type_Name__mdt` | `Config_Setting__mdt` |
| Platform Event | `Event_Name__e` | `Order_Event__e` |
| Big Object | `Object_Name__b` | `Archive__b` |
| External Object | `Object_Name__x` | `ERP_Order__x` |

---

## ID Formats

| Format | Length | Example |
|--------|--------|---------|
| 15-char (case-sensitive) | 15 | `001AB000003xyz` |
| 18-char (case-insensitive) | 18 | `001AB000003xyzAAA` |

**Key Prefix Codes:**
| Prefix | Object |
|--------|--------|
| `001` | Account |
| `003` | Contact |
| `005` | User |
| `006` | Opportunity |
| `00Q` | Lead |
| `500` | Case |
| `00T` | Task |
| `00U` | Event |
| `01p` | ApexClass |
| `01q` | ApexTrigger |
