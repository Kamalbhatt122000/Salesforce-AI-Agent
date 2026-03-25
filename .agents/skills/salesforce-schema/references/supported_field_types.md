# Schema Management — Supported Field Types Reference

## Custom Field Types

| Type | Description | Key Parameters | API Value |
|------|-------------|----------------|-----------|
| **Text** | Single-line string | `length` (max: 255) | `Text` |
| **Number** | Integer or decimal | `precision`, `scale` | `Number` |
| **Checkbox** | Boolean true/false | `defaultValue` | `Checkbox` |
| **Date** | Date only (no time) | — | `Date` |
| **DateTime** | Date + time | — | `DateTime` |
| **Email** | Email validation | — | `Email` |
| **Phone** | Phone number | — | `Phone` |
| **URL** | Web link | — | `Url` |
| **Currency** | Money values | `precision`, `scale` | `Currency` |
| **Percent** | Percentage | `precision`, `scale` | `Percent` |
| **TextArea** | Multi-line (255 chars) | — | `TextArea` |
| **LongTextArea** | Large text (32,768+) | `length`, `visibleLines` | `LongTextArea` |
| **Rich Text** | HTML-formatted text | `length`, `visibleLines` | `Html` |
| **Picklist** | Single-select dropdown | `valueSet` | `Picklist` |
| **Multi-Select Picklist** | Multi-select dropdown | `valueSet` | `MultiselectPicklist` |
| **Lookup** | Relationship to another object | `referenceTo` | `Lookup` |
| **Master-Detail** | Parent-child relationship | `referenceTo` | `MasterDetail` |
| **Auto Number** | Auto-incrementing label | `displayFormat`, `startingNumber` | `AutoNumber` |
| **Formula** | Calculated field | `formula`, `formulaTreatBlanksAs` | `*` (depends on return type) |

## Precision & Scale Explained

- **Precision**: Total number of digits (including both sides of decimal)
- **Scale**: Number of digits after the decimal point

| Example | Precision | Scale | Max Value |
|---------|-----------|-------|-----------|
| `18, 0` | 18 | 0 | 999,999,999,999,999,999 |
| `18, 2` | 18 | 2 | 9,999,999,999,999,999.99 |
| `5, 2` | 5 | 2 | 999.99 |

## Naming Conventions

- **Label**: Human-readable name (e.g., "Priority Score")
- **API Name**: Auto-generated with `__c` suffix (e.g., `Priority_Score__c`)
- Custom fields on standard objects: `Lead.Priority_Score__c`
- Custom fields on custom objects: `Invoice__c.Line_Total__c`
- Cannot start with a number
- Cannot contain spaces (replaced with underscores)

## Standard vs Custom

| Aspect | Standard Objects | Custom Objects |
|--------|-----------------|----------------|
| Suffix | None | `__c` |
| Examples | `Account`, `Contact`, `Lead` | `Invoice__c`, `Project__c` |
| Can delete? | No | Yes |
| Custom fields on them | Yes (end in `__c`) | Yes (end in `__c`) |

## Tooling API for Custom Fields

### Create Custom Field

```
POST /services/data/v62.0/tooling/sobjects/CustomField/
```

**Payload**:
```json
{
  "FullName": "Lead.Priority_Score__c",
  "Metadata": {
    "label": "Priority Score",
    "type": "Number",
    "precision": 5,
    "scale": 0,
    "description": "Lead priority score from 1-100"
  }
}
```

### Delete Custom Field

1. Query the field ID:
```
GET /services/data/v62.0/tooling/query/?q=SELECT Id FROM CustomField WHERE TableEnumOrId='Lead' AND DeveloperName='Priority_Score'
```

2. Delete by ID:
```
DELETE /services/data/v62.0/tooling/sobjects/CustomField/{fieldId}
```

## Limits

| Limit | Value |
|-------|-------|
| Custom fields per object | 500 (Enterprise), 800 (Unlimited) |
| Picklist values per field | 1,000 |
| Custom objects per org | 200 (Enterprise), 2,000 (Unlimited) |
| Relationship fields per object | 40 |
| Field label max length | 40 characters |
