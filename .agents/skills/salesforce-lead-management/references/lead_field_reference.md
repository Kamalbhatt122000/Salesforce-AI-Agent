# Lead Management — Lead Field Reference

## Lead Lifecycle

```
Open - Not Contacted → Working - Contacted → Closed - Converted
                                            → Closed - Not Converted
```

## Lead Fields

| Display Name | API Name | Type | Required |
|-------------|----------|------|----------|
| First Name | `FirstName` | Text | No |
| Last Name | `LastName` | Text | **Yes** |
| Company | `Company` | Text | **Yes** |
| Email | `Email` | Email | No |
| Phone | `Phone` | Phone | No |
| Mobile | `MobilePhone` | Phone | No |
| Title | `Title` | Text | No |
| Status | `Status` | Picklist | No |
| Lead Source | `LeadSource` | Picklist | No |
| Industry | `Industry` | Picklist | No |
| Rating | `Rating` | Picklist | No |
| Website | `Website` | URL | No |
| Street | `Street` | TextArea | No |
| City | `City` | Text | No |
| State | `State` | Text | No |
| Postal Code | `PostalCode` | Text | No |
| Country | `Country` | Text | No |
| Description | `Description` | TextArea | No |

## Standard Status Values

| Status | API Value | Stage |
|--------|-----------|-------|
| Open - Not Contacted | `Open - Not Contacted` | Open |
| Working - Contacted | `Working - Contacted` | Open |
| Closed - Converted | `Closed - Converted` | Closed (Won) |
| Closed - Not Converted | `Closed - Not Converted` | Closed (Lost) |

## Lead Conversion Mapping

When a Lead is converted to `Closed - Converted`, the following mapping is used:

| Lead Field | → Account Field | → Contact Field |
|-----------|----------------|----------------|
| `Company` | `Name` | — |
| `FirstName` | — | `FirstName` |
| `LastName` | — | `LastName` |
| `Email` | — | `Email` |
| `Phone` | `Phone` | `Phone` |
| `Title` | — | `Title` |
| `Website` | `Website` | — |
| `Industry` | `Industry` | — |
| `Description` | `Description` | — |
| `Street` | `BillingStreet` | `MailingStreet` |
| `City` | `BillingCity` | `MailingCity` |
| `State` | `BillingState` | `MailingState` |
| `PostalCode` | `BillingPostalCode` | `MailingPostalCode` |
| `Country` | `BillingCountry` | `MailingCountry` |

## Common Lead Queries

```sql
-- All open leads
SELECT Id, Name, Company, Status, LeadSource FROM Lead WHERE IsConverted = false

-- Leads by source
SELECT LeadSource, COUNT(Id) FROM Lead GROUP BY LeadSource

-- Leads created this month
SELECT Id, Name, CreatedDate FROM Lead WHERE CreatedDate = THIS_MONTH

-- Specific lead by ID
SELECT Id, FirstName, LastName, Company, Email, Phone, MobilePhone, Status
FROM Lead WHERE Id = '00Qxxxx'

-- Hot leads (high rating)
SELECT Id, Name, Company, Rating FROM Lead WHERE Rating = 'Hot' AND IsConverted = false
```

## Conversion Rules

- Lead conversion is **irreversible** — once converted, cannot be reverted
- If an Account with the same Company name exists, the Contact is linked to it
- If no matching Account exists, a new Account is created
- A new Contact is always created during conversion
- Optionally, an Opportunity can be created during conversion
