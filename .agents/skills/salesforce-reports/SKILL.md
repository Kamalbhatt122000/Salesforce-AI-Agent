---
name: salesforce-reports
description: Browse, search, run, and interpret Salesforce reports (Tabular, Summary, Matrix). Use when the user asks to list reports, run a specific report, view report folders, filter report results, or chart report data. Supports runtime filters and auto-generates charts from grouped report data.
metadata:
  author: salesforce-ai-agent
  version: "1.0"
  category: analytics
  tier: 2
  dependencies:
    - salesforce-auth
    - salesforce-analytics
---

# Salesforce Reports Skill

Browse, run, and interpret native Salesforce reports via the Analytics API.

## Prerequisites

- Authenticated Salesforce connection (see `salesforce-auth` skill)
- User must have access to the report folder (Public, Shared, or Private/owned)

## Available Tools

| Tool | Purpose |
|------|---------|
| `list_report_folders` | List all report folders the user can access |
| `list_reports` | List reports, optionally filtered by folder or search term |
| `get_report_metadata` | Get report structure: columns, groupings, filters |
| `run_report` | Execute a report and return rows, aggregates, and groupings |
| `generate_chart` | Visualize report aggregate data as a chart |

## Required Workflow

**Follow these steps in order.**

### Step 1: Discover Reports

When the user asks about reports without specifying one:

1. Call `list_reports` (optionally with `search_term` if user mentioned a topic)
2. Present results in a table: **Name | Folder | Format | Last Run**
3. Ask which report to run, or proceed if user already named one

When the user asks about folders:

1. Call `list_report_folders`
2. Present folders grouped by access type (Public / Shared / Private)

### Step 2: (Optional) Inspect Report Structure

Before running, if the user wants to understand the report or apply filters:

1. Call `get_report_metadata` with the `report_id`
2. Show the columns, groupings, and existing filters
3. Offer to apply runtime filters before running

### Step 3: Run the Report

1. Call `run_report` with the `report_id`
2. Optionally pass `filters` array for runtime filtering
3. Present results — see **Presenting Results** section below

### Step 4: Visualize (if grouped data exists)

If the report has groupings and aggregates:

1. Call `generate_chart` using the group labels and aggregate values
2. Choose chart type based on the data (see chart selection guide)

## Presenting Results

### Always do this after `run_report`:

- The A2UI surface (report title + KPI cards + metadata footer) is **automatically rendered** — do NOT duplicate it in text
- Show data rows in a **Markdown table** (max 20 rows; mention total if more exist)
- If the report has groupings, organize the table by group
- If group aggregates exist, a chart is automatically generated
- End with a 1–2 sentence insight summary
- Offer to: filter, chart, export, or drill down

### Format by Report Type

| Report Format | How to Present |
|---------------|----------------|
| **Tabular** | Simple table of all rows. Show totals from aggregates if present. |
| **Summary** | Group rows under their group heading. Show subtotals per group. |
| **Matrix** | Show grand totals and top-level row data. Note it's a matrix report. |

## Runtime Filters

Pass filters as an array to `run_report`:

```json
[
  { "column": "STAGE_NAME", "operator": "equals", "value": "Prospecting" },
  { "column": "CLOSE_DATE", "operator": "greaterThan", "value": "2024-01-01" }
]
```

### Filter Operators

| Operator | Meaning |
|----------|---------|
| `equals` | Exact match |
| `notEqual` | Not equal |
| `greaterThan` | Greater than |
| `lessThan` | Less than |
| `greaterOrEqual` | Greater than or equal |
| `lessOrEqual` | Less than or equal |
| `contains` | Text contains |
| `notContain` | Text does not contain |
| `startsWith` | Text starts with |
| `includes` | Picklist includes value |
| `excludes` | Picklist excludes value |

## Report Folder Access

| Access Type | Who Can See |
|-------------|-------------|
| **Public** | All users in the org |
| **Shared** | Specific users, roles, or groups |
| **Private** | Only the folder owner |
| **All** | Every report the current user can access |

## Report Formats

| Format | Description | Chart Support |
|--------|-------------|---------------|
| **Tabular** | Flat list of rows, like a spreadsheet | Aggregates only |
| **Summary** | Rows grouped by one or more fields, with subtotals | Yes — group aggregates |
| **Matrix** | Rows AND columns grouped, with cross-tabulation | Grand totals |
| **Joined** | Multiple report blocks in one | Limited |

## Key Rules

- **NEVER ask the user for a report ID** — always use names from `list_reports` results
- **NEVER run a report without first listing** if the user hasn't specified one
- **NEVER duplicate the A2UI surface** — it renders automatically; just show the data table
- If the report returns 0 rows, say so clearly and suggest checking filters or folder access
- If `totalRows` > rows returned, tell the user: "Showing X of Y rows"

## References

| Document | Contents |
|----------|----------|
| [Report API Reference](references/report_api_reference.md) | Analytics API endpoints, factMap structure, filter operators, error codes |
| [Report Patterns](references/report_patterns.md) | Common report workflows, filter examples, chart mapping, troubleshooting |
