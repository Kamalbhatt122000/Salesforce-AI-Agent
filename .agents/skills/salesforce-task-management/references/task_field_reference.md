# Task & Event Field Reference

## Task Object — Field API Names

### Standard Fields

| Field API Name | Label | Type | Required | Notes |
|---------------|-------|------|----------|-------|
| `Id` | Task ID | ID | Auto | Starts with `00T` |
| `Subject` | Subject | Combobox | Yes | Free text or picklist: Call, Email, Send Letter, Send Quote, Other |
| `Status` | Status | Picklist | Yes | Not Started, In Progress, Completed, Waiting on someone else, Deferred |
| `Priority` | Priority | Picklist | Yes | High, Normal, Low |
| `ActivityDate` | Due Date Only | Date | No | Format: YYYY-MM-DD |
| `Description` | Comments | TextArea | No | Free-form notes |
| `WhoId` | Name | Reference | No | Lead (00Q) or Contact (003) |
| `WhatId` | Related To | Reference | No | Account (001), Opportunity (006), Case (500) |
| `OwnerId` | Assigned To | Reference | No | Defaults to current user |
| `IsReminderSet` | Reminder | Boolean | No | Default: false |
| `ReminderDateTime` | Reminder Date/Time | DateTime | No | Only used if IsReminderSet = true |
| `TaskSubtype` | Task Subtype | Picklist | No | Task, Call, Email |
| `IsClosed` | Closed | Boolean | Read-only | True when Status = Completed or Deferred |
| `IsHighPriority` | High Priority | Boolean | Read-only | True when Priority = High |
| `CreatedDate` | Created Date | DateTime | Auto | When the task was created |
| `LastModifiedDate` | Last Modified | DateTime | Auto | When the task was last updated |
| `CompletedDateTime` | Completed Date | DateTime | Auto | When Status was set to Completed |

### Status Values Mapping

| Status | IsClosed | Description |
|--------|----------|-------------|
| `Not Started` | false | Default for new tasks |
| `In Progress` | false | Currently being worked on |
| `Completed` | true | Successfully finished |
| `Waiting on someone else` | false | Blocked/waiting |
| `Deferred` | true | Postponed/cancelled |

### Subject Picklist Values (Standard)
- Call
- Email
- Send Letter
- Send Quote
- Other

## Event Object — Field API Names

### Standard Fields

| Field API Name | Label | Type | Required | Notes |
|---------------|-------|------|----------|-------|
| `Id` | Event ID | ID | Auto | Starts with `00U` |
| `Subject` | Subject | Combobox | Yes | Free text or picklist |
| `StartDateTime` | Start Date/Time | DateTime | Yes | ISO format: YYYY-MM-DDTHH:MM:SS |
| `EndDateTime` | End Date/Time | DateTime | Yes* | *Required unless DurationInMinutes is set |
| `DurationInMinutes` | Duration | Integer | No | Alternative to EndDateTime |
| `Location` | Location | String | No | Physical or virtual location |
| `Description` | Description | TextArea | No | Meeting agenda/notes |
| `WhoId` | Name | Reference | No | Lead or Contact |
| `WhatId` | Related To | Reference | No | Account, Opportunity, etc. |
| `OwnerId` | Assigned To | Reference | No | Defaults to current user |
| `IsAllDayEvent` | All-Day Event | Boolean | No | If true, use ActivityDate instead of StartDateTime |
| `IsPrivate` | Private | Boolean | No | Only visible to owner |
| `ShowAs` | Show Time As | Picklist | No | Busy, Free, OutOfOffice |
| `CreatedDate` | Created Date | DateTime | Auto | |
| `LastModifiedDate` | Last Modified | DateTime | Auto | |

### Event Subject Picklist Values (Standard)
- Call
- Email
- Meeting
- Other
- Send Letter/Quote

## Common SOQL Queries

### Task Queries

```sql
-- All open tasks (not completed)
SELECT Id, Subject, Status, Priority, ActivityDate, Who.Name, What.Name
FROM Task WHERE Status != 'Completed' AND Status != 'Deferred'
ORDER BY ActivityDate ASC NULLS LAST

-- My overdue tasks
SELECT Id, Subject, Status, Priority, ActivityDate, Who.Name
FROM Task WHERE ActivityDate < TODAY AND IsClosed = false
ORDER BY ActivityDate ASC

-- Tasks due this week
SELECT Id, Subject, Status, Priority, ActivityDate, Who.Name, What.Name
FROM Task WHERE ActivityDate = THIS_WEEK
ORDER BY ActivityDate ASC

-- High priority open tasks
SELECT Id, Subject, Status, ActivityDate, Who.Name, What.Name
FROM Task WHERE Priority = 'High' AND IsClosed = false
ORDER BY ActivityDate ASC

-- Tasks related to a specific account
SELECT Id, Subject, Status, Priority, ActivityDate
FROM Task WHERE WhatId = '001XXXXXXXX'
ORDER BY ActivityDate DESC

-- Recently completed tasks
SELECT Id, Subject, CompletedDateTime, Who.Name, What.Name
FROM Task WHERE IsClosed = true
ORDER BY CompletedDateTime DESC LIMIT 20

-- Tasks grouped by status
SELECT Status, COUNT(Id) cnt
FROM Task
GROUP BY Status

-- Tasks grouped by priority
SELECT Priority, COUNT(Id) cnt
FROM Task WHERE IsClosed = false
GROUP BY Priority

-- Tasks created this month
SELECT Id, Subject, Status, Priority, ActivityDate, CreatedDate
FROM Task WHERE CreatedDate = THIS_MONTH
ORDER BY CreatedDate DESC
```

### Event Queries

```sql
-- Upcoming events (next 7 days)
SELECT Id, Subject, StartDateTime, EndDateTime, Location, Who.Name, What.Name
FROM Event WHERE StartDateTime >= TODAY AND StartDateTime <= NEXT_N_DAYS:7
ORDER BY StartDateTime ASC

-- Events this week
SELECT Id, Subject, StartDateTime, EndDateTime, Location
FROM Event WHERE StartDateTime = THIS_WEEK
ORDER BY StartDateTime ASC

-- Today's events
SELECT Id, Subject, StartDateTime, EndDateTime, Location, Who.Name
FROM Event WHERE ActivityDate = TODAY
ORDER BY StartDateTime ASC

-- Events with a specific contact
SELECT Id, Subject, StartDateTime, EndDateTime, Location
FROM Event WHERE WhoId = '003XXXXXXXX'
ORDER BY StartDateTime DESC

-- All-day events this month
SELECT Id, Subject, ActivityDate, Who.Name
FROM Event WHERE IsAllDayEvent = true AND ActivityDate = THIS_MONTH
```

## Linking Guide

### WhoId (Person — Lead or Contact)
- Use when the task/event is **about** a person
- Lead IDs start with `00Q`
- Contact IDs start with `003`
- Only ONE WhoId per Task/Event

### WhatId (Object — Account, Opportunity, Case)
- Use when the task/event **relates to** a business object
- Account IDs start with `001`
- Opportunity IDs start with `006`
- Case IDs start with `500`
- Only ONE WhatId per Task/Event

### Combination Rules
- A Task can have **both** WhoId AND WhatId
- WhoId tells you WHO is involved
- WhatId tells you WHAT it's related to
- Example: Task "Call about renewal" → WhoId = Contact, WhatId = Opportunity
