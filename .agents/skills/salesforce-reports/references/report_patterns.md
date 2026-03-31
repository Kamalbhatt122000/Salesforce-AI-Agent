# Salesforce Report Patterns

## Common Workflows

### Pattern 1: "Show me all reports"

```
1. list_reports()
2. Present table: Name | Folder | Format | Last Run
3. Ask: "Which report would you like to run?"
```

### Pattern 2: "Show me reports about leads"

```
1. list_reports(search_term="lead")
2. Present filtered table
3. Offer to run any of them
```

### Pattern 3: "Run the [report name] report"

```
1. list_reports(search_term="[report name]")  ← find the ID
2. run_report(report_id)
3. Present results table + auto-rendered A2UI surface
4. If groupings exist → generate_chart()
```

### Pattern 4: "Run the report but only for this quarter"

```
1. get_report_metadata(report_id)  ← find the correct column API name for date field
2. run_report(report_id, filters=[
     { "column": "CLOSE_DATE", "operator": "greaterOrEqual", "value": "2024-01-01" },
     { "column": "CLOSE_DATE", "operator": "lessOrEqual",    "value": "2024-03-31" }
   ])
3. Present results
```

### Pattern 5: "What reports are in the Sales folder?"

```
1. list_report_folders()  ← find the folder ID for "Sales"
2. list_reports(folder_id="[folder_id]")
3. Present reports in that folder
```

### Pattern 6: "Show me the structure of this report"

```
1. get_report_metadata(report_id)
2. Present: columns table, groupings, existing filters
3. Offer to run it or apply additional filters
```

---

## Chart Mapping from Report Data

After running a Summary or Matrix report, map aggregate data to a chart:

### Summary Report → Bar Chart

```python
group_aggs = result["aggregates"]["_group_aggregates"]
labels = [g["group"] for g in group_aggs]
data   = [g["value"] for g in group_aggs]

generate_chart(
    chart_type = "bar" if len(labels) <= 8 else "horizontalBar",
    title      = result["name"],
    labels     = labels,
    data       = data,
    dataset_label = group_aggs[0]["label"]  # e.g. "Sum of Amount"
)
```

### Tabular Report → No chart (no groupings)

For tabular reports, only show the data table. Charts require grouped data.

### When to Auto-Chart

| Condition | Action |
|-----------|--------|
| Report has groupings AND aggregates | Auto-generate chart after running |
| Report is Tabular with no aggregates | Show table only |
| User explicitly asks for a chart | Always generate one |
| Report has 1 group, multiple aggregates | Chart the primary aggregate |

---

## Filter Column Names

Report filter columns use **API column names**, not display labels.
Always call `get_report_metadata` first to get the correct column names.

### Common Column Name Patterns

| Object | Display Label | Typical Column API Name |
|--------|---------------|------------------------|
| Opportunity | Stage | `STAGE_NAME` |
| Opportunity | Close Date | `CLOSE_DATE` |
| Opportunity | Amount | `AMOUNT` |
| Opportunity | Owner | `OPPORTUNITY_NAME` |
| Lead | Status | `LEAD_STATUS` |
| Lead | Lead Source | `LEAD_SOURCE` |
| Lead | Rating | `RATING` |
| Account | Industry | `INDUSTRY` |
| Case | Priority | `PRIORITY` |
| Case | Status | `STATUS` |

> **Note**: Column names vary by report type and org configuration.
> Always use `get_report_metadata` to get the exact names for a specific report.

---

## Presenting Report Results

### Tabular Report

```markdown
**[Report Name]** — Tabular · [N] rows

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value    | Value    | Value    |
...

*Showing 20 of 150 rows. Total: $1.2M*
```

### Summary Report

```markdown
**[Report Name]** — Summary · [N] rows

**Group: Prospecting** (12 records, $450K)
| Name | Amount | Close Date |
|------|--------|------------|
| ...  | ...    | ...        |

**Group: Qualification** (8 records, $320K)
| Name | Amount | Close Date |
|------|--------|------------|
| ...  | ...    | ...        |

**Grand Total: 20 records, $770K**
```

### Matrix Report

```markdown
**[Report Name]** — Matrix

Grand totals are shown in the KPI cards above.
Top-level data:

| Row Group | Value |
|-----------|-------|
| ...       | ...   |
```

---

## Troubleshooting

### "Report returns 0 rows"

1. Check if runtime filters are too restrictive
2. Verify the user has access to the records (OWD / sharing rules)
3. Check if the report's built-in filters exclude the expected data
4. Try running without filters first

### "INSUFFICIENT_ACCESS error"

- The report is in a Private folder owned by someone else
- The user's profile doesn't have "Run Reports" permission
- The report references objects the user can't see

### "INVALID_FILTER_COLUMN error"

- The column API name is wrong
- Call `get_report_metadata` to get the exact column names
- Column names are case-sensitive

### "Report shows stale data"

- Salesforce reports run against live data — results are always current
- If data looks wrong, check the report's built-in date filters

### "Too many rows — report is slow"

- Add runtime filters to narrow the result set
- The API caps results at 2,000 rows per run
- For full data exports, use Bulk API instead

---

## Report Format Decision Guide

| User Says | Report Format to Look For |
|-----------|--------------------------|
| "Show me a list of all leads" | Tabular |
| "Show leads grouped by status" | Summary |
| "Show revenue by rep by month" | Matrix |
| "Show me the pipeline report" | Summary (grouped by Stage) |
| "Show me the forecast" | Summary or Matrix |

---

## Integration with Analytics Dashboard

The `get_analytics_dashboard` tool (permission-aware) is preferred over raw reports for:

- `my_pipeline` — open opportunities
- `deals_at_risk` — overdue deals
- `tasks_today` — tasks due today
- `team_performance` — rep leaderboard
- `forecast` — closed won vs pipeline
- `no_activity_accounts` — inactive accounts
- `sla_risk_cases` — high-priority open cases
- `data_quality` — missing fields

Use the **Reports skill** when the user explicitly asks about a named Salesforce report,
wants to browse report folders, or needs to run a custom report with specific filters.
