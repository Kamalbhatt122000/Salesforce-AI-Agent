---
name: salesforce-task-management
description: Manage the full task and event lifecycle in Salesforce — create tasks, update task status, assign tasks, set due dates, log calls, book meetings, and track activity history. Use when the user mentions tasks, to-dos, follow-ups, meetings, calls, events, or activity management. Supports all four CRUD operations on Task and Event objects.
metadata:
  author: salesforce-ai-agent
  version: "1.0"
  category: crm-workflow
  tier: 2
  dependencies:
    - salesforce-auth
    - salesforce-crud
    - salesforce-query
---

# Salesforce Task Management Skill

Handle the complete task and event lifecycle: creation, assignment, status tracking, and completion.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- Task and Event objects must be available in the org

## Available Tools

| Tool | Purpose |
|------|---------|
| `create_record` | Create a new Task or Event |
| `update_record` | Update Task/Event fields (status, due date, priority, etc.) |
| `delete_record` | Delete a Task or Event by ID |
| `get_record_all_fields` | Fetch complete Task/Event details by ID |
| `run_soql_query` | Query tasks/events by criteria |
| `check_calendar` | Check calendar availability before booking |
| `book_meeting` | Book a meeting (creates an Event) |
| `render_create_form` | Render interactive form for Task/Event creation |

## Task Object Fields

### Required Fields
| Field API Name | Label | Type |
|---------------|-------|------|
| `Subject` | Subject | Picklist/Text |
| `Status` | Status | Picklist |
| `Priority` | Priority | Picklist |

### Common Fields
| Field API Name | Label | Type | Description |
|---------------|-------|------|-------------|
| `Subject` | Subject | Text | Task subject/title (e.g. "Call", "Follow Up", "Send Quote") |
| `Status` | Status | Picklist | Not Started, In Progress, Completed, Waiting on someone else, Deferred |
| `Priority` | Priority | Picklist | High, Normal, Low |
| `ActivityDate` | Due Date | Date | Task due date (YYYY-MM-DD format) |
| `Description` | Comments | TextArea | Task description or notes |
| `WhoId` | Name (Related To Person) | Lookup | Lead ID (00Q...) or Contact ID (003...) |
| `WhatId` | Related To (Object) | Lookup | Account ID (001...), Opportunity ID (006...), Case ID (500...) |
| `OwnerId` | Assigned To | Lookup | User ID — defaults to current user if not specified |
| `IsReminderSet` | Reminder | Boolean | Whether to set a reminder |
| `ReminderDateTime` | Reminder Date/Time | DateTime | When to remind |
| `TaskSubtype` | Subtype | Picklist | "Task", "Call", "Email" |

### Task Status Values
```
Not Started → In Progress → Completed
                          → Waiting on someone else
                          → Deferred
```

### Task Priority Values
- **High** — Urgent, needs immediate attention
- **Normal** — Standard priority (default)
- **Low** — Can be deferred

## Event Object Fields

### Required Fields
| Field API Name | Label | Type |
|---------------|-------|------|
| `Subject` | Subject | String |
| `StartDateTime` | Start | DateTime |
| `EndDateTime` | End | DateTime |

### Common Fields
| Field API Name | Label | Type | Description |
|---------------|-------|------|-------------|
| `Subject` | Subject | Text | Event title (e.g. "Meeting with client") |
| `StartDateTime` | Start Date/Time | DateTime | Event start (ISO format) |
| `EndDateTime` | End Date/Time | DateTime | Event end (ISO format) |
| `DurationInMinutes` | Duration | Number | Alternative to EndDateTime |
| `Location` | Location | Text | Meeting location |
| `Description` | Description | TextArea | Meeting agenda or notes |
| `WhoId` | Name | Lookup | Lead or Contact ID |
| `WhatId` | Related To | Lookup | Account or Opportunity ID |
| `IsAllDayEvent` | All-Day Event | Boolean | Whether the event spans the entire day |

## Required Workflow

### Creating a Task

1. Extract the **Subject** from the user's request (e.g. "Follow up", "Call", "Send proposal")
2. Extract the **due date** if mentioned (convert natural language to YYYY-MM-DD)
3. Determine the **WhoId** (Lead/Contact) or **WhatId** (Account/Opportunity) from context
4. If the user does NOT provide all required fields → use `render_create_form` with `object_name="Task"`
5. If the user provides Subject + Status + Priority → use `create_record` directly
6. Default values if not specified:
   - Status: "Not Started"
   - Priority: "Normal"

### Updating a Task

1. Use `update_record` with the Task ID and changed fields
2. Common updates: Status change, Priority change, Due date change, Reassignment

### Deleting a Task

1. Use `delete_record` with `object_name="Task"` and the Task ID
2. Task IDs start with `00T`

### Booking a Meeting / Creating an Event

1. ALWAYS call `check_calendar` first to verify availability
2. Use `book_meeting` for simple meeting creation
3. For complex events, use `create_record` with `object_name="Event"`

### Querying Tasks

Common task queries:
```sql
-- All open tasks for the current user
SELECT Id, Subject, Status, Priority, ActivityDate, Who.Name, What.Name 
FROM Task WHERE Status != 'Completed' ORDER BY ActivityDate ASC

-- Overdue tasks
SELECT Id, Subject, Status, ActivityDate, Who.Name 
FROM Task WHERE ActivityDate < TODAY AND Status != 'Completed'

-- Tasks due this week
SELECT Id, Subject, Status, Priority, ActivityDate 
FROM Task WHERE ActivityDate = THIS_WEEK

-- Tasks related to a specific account
SELECT Id, Subject, Status, ActivityDate 
FROM Task WHERE WhatId = '001xxxx'

-- Completed tasks this month
SELECT Id, Subject, Status, ActivityDate 
FROM Task WHERE Status = 'Completed' AND ActivityDate = THIS_MONTH

-- Tasks by priority
SELECT Priority, COUNT(Id) cnt FROM Task WHERE Status != 'Completed' GROUP BY Priority
```

### Querying Events

```sql
-- Upcoming events
SELECT Id, Subject, StartDateTime, EndDateTime, Location, Who.Name 
FROM Event WHERE StartDateTime >= TODAY ORDER BY StartDateTime ASC

-- Events this week
SELECT Id, Subject, StartDateTime, EndDateTime, Location 
FROM Event WHERE StartDateTime = THIS_WEEK

-- Events with a specific contact
SELECT Id, Subject, StartDateTime, Location 
FROM Event WHERE WhoId = '003xxxx'
```

## Linking Rules

| Link Field | Used For | ID Prefix |
|------------|----------|-----------|
| `WhoId` | Lead or Contact (person) | 00Q (Lead), 003 (Contact) |
| `WhatId` | Account, Opportunity, Case (object) | 001 (Account), 006 (Opportunity), 500 (Case) |

**Important:**
- A Task can have BOTH a WhoId and a WhatId
- WhoId is for the **person** the task is about
- WhatId is for the **object** the task is related to
- For Tasks linked to Accounts, use **WhatId** (not WhoId)

## Bulk Task Creation

When the user asks to create tasks for multiple records (e.g. "create follow-up tasks for all inactive accounts"):

1. Use the record IDs from a previous query in the conversation
2. Create tasks one by one using `create_record` in sequence
3. Use sensible defaults from the user's instruction:
   - Subject: derived from user's words
   - ActivityDate: convert natural language dates to YYYY-MM-DD
   - Status: "Not Started"
   - Priority: "Normal"
4. Show a summary table when all tasks are created

## Record ID Prefixes

| Prefix | Object |
|--------|--------|
| `00T` | Task |
| `00U` | Event |
| `001` | Account |
| `003` | Contact |
| `00Q` | Lead |
| `006` | Opportunity |
| `500` | Case |

## References

| Document | Contents |
|----------|----------|
| [Task Field Reference](references/task_field_reference.md) | Complete field API names, status values, and common queries for Task and Event |
