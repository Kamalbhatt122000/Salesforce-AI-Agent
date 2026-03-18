# Flows & Automation — Salesforce

## Overview

Salesforce Flow is the primary declarative automation tool. It allows building complex business processes with clicks (no code). Flows can be triggered by record changes, scheduled times, platform events, or user interaction.

## Flow Types

| Type | Trigger | Use Case |
|------|---------|----------|
| **Screen Flow** | User clicks a button/link | Guided user interactions, wizards, data entry |
| **Record-Triggered Flow** | Record create/update/delete | Auto-populate fields, create related records, send notifications |
| **Scheduled Flow** | Cron schedule | Periodic data cleanup, batch updates, reminders |
| **Platform Event-Triggered Flow** | Platform Event received | React to events from external systems |
| **Autolaunched Flow** | Called by Apex, another flow, or process | Reusable sub-flows, background processing |

---

## Record-Triggered Flows

The most commonly used flow type. Replaces Workflow Rules and Process Builder.

### Trigger Configurations

| When | Timing | What You Can Do |
|------|--------|----------------|
| **A record is created** | Before Save | Set field values on the record |
| **A record is updated** | Before Save | Set field values before commit |
| **A record is created** | After Save | Create/update other records, send emails, call Apex |
| **A record is updated** | After Save | Create/update other records, post to Chatter |
| **A record is deleted** | After Delete | Clean up related records, log deletion |

### Before-Save vs After-Save

| Before Save | After Save |
|-------------|------------|
| Faster (no extra DML) | Triggers additional DML |
| Can only modify the triggering record | Can create/update other records |
| No Id available on insert | Id is available |
| Can't send emails | Can send emails |
| Can't call Apex actions | Can call Apex actions |

### Entry Conditions
Define which records trigger the flow:
- **All records** — runs on every create/update
- **Condition requirements** — filter by field values
- **Formula** — custom formula evaluates to `true`

### Key Flow Elements

| Element | Purpose |
|---------|---------|
| **Assignment** | Set variable values |
| **Decision** | Branch logic (if/else) |
| **Loop** | Iterate over a collection |
| **Get Records** | Query Salesforce data (SOQL) |
| **Create Records** | Insert new records |
| **Update Records** | Update existing records |
| **Delete Records** | Delete records |
| **Action** | Call Apex, send email, post to Chatter, invoke REST |
| **Subflow** | Call another flow |
| **Screen** | Display a UI to the user (Screen Flows only) |

---

## Screen Flows

Interactive flows that display screens to users.

### Screen Components
- **Text Input** — Single-line text entry
- **Text Area** — Multi-line text
- **Number** — Numeric input
- **Date/DateTime** — Date pickers
- **Picklist** — Dropdown selection
- **Radio Buttons** — Single selection
- **Checkbox** — Boolean input
- **Lookup** — Record search
- **Display Text** — Read-only info
- **Data Table** — Display records in table format

### Launching Screen Flows
- **Lightning Page** (Flow component)
- **Quick Action** on a record
- **Custom Button** or Link
- **Experience Cloud** pages
- `{instance_url}/flow/MyFlowName`

---

## Scheduled Flows

Run on a schedule to process batches of records.

### Configuration
1. Set the **object** and **entry conditions**
2. Define the **schedule** (daily, weekly, specific time)
3. Add actions to perform on each record

### Use Cases
- Send reminder emails for overdue tasks
- Archive old records
- Update statuses based on date thresholds

---

## Platform Event-Triggered Flows

Start when a Platform Event is published.

### Configuration
1. Select the **Platform Event** (e.g., `Order_Event__e`)
2. Define conditions on event fields
3. Process the event data and create/update records

---

## Flow Best Practices

1. **Use Before-Save flows** when only updating the triggering record (more efficient)
2. **Bulkify flows** — they handle multiple records, but be mindful of loop complexity
3. **Avoid redundant queries** — use `Get Records` once and reference the variable
4. **Use Subflows** for reusable logic
5. **Add Fault Paths** for error handling
6. **Use Entry Conditions** to limit when the flow runs
7. **Version your flows** — deactivate old versions after testing

## Flow Limits

| Limit | Value |
|-------|-------|
| Max flow interviews per transaction | 2,000 |
| Max executed elements per interview | 2,000 |
| Max SOQL queries (via Get Records) | 100 per transaction |
| Max DML statements | 150 per transaction |
| Max record creates/updates per element | 200 records |

---

## Automation Tool Comparison

| Feature | Record-Triggered Flow | Apex Trigger | Workflow Rule (Legacy) |
|---------|----------------------|--------------|----------------------|
| Complexity | Low-Medium | High | Low |
| Code required | No | Yes | No |
| Before-save logic | Yes | Yes | No |
| Cross-object updates | Yes | Yes | Limited |
| Callouts | Yes (via Apex action) | Yes | No |
| Recommended | ✅ Yes | For complex logic | ❌ Deprecated |
