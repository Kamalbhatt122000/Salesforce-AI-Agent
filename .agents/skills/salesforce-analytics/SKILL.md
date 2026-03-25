---
name: salesforce-analytics
description: Generate charts, reports, and data visualizations from Salesforce data. Use when the user asks for charts, graphs, visual summaries, reports on leads/accounts/opportunities, or data analysis. Supports bar, pie, doughnut, line, and horizontal bar charts.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: analytics
  tier: 2
  dependencies:
    - salesforce-auth
    - salesforce-query
---

# Salesforce Analytics & Visualization Skill

Generate charts and visual analytics from Salesforce data.

## Prerequisites

- Authenticated Salesforce connection
- Data to visualize (usually from a SOQL aggregate query)

## Available Tools

| Tool | Purpose |
|------|---------|
| `run_soql_query` | Execute aggregate SOQL queries to get chart data |
| `generate_chart` | Generate a chart visualization from data |

## Required Workflow

**Follow these steps in order.**

### Step 1: Query the Data

Run an aggregate SOQL query to get the data for visualization:

```sql
-- Leads by status (good for pie/bar chart)
SELECT Status, COUNT(Id) cnt FROM Lead GROUP BY Status

-- Opportunities by stage (good for horizontal bar)
SELECT StageName, COUNT(Id) cnt FROM Opportunity GROUP BY StageName

-- Revenue by month (good for line chart)
SELECT CALENDAR_MONTH(CloseDate) month, SUM(Amount) total FROM Opportunity 
WHERE IsWon = true GROUP BY CALENDAR_MONTH(CloseDate) ORDER BY CALENDAR_MONTH(CloseDate)

-- Accounts by industry (good for doughnut)
SELECT Industry, COUNT(Id) cnt FROM Account WHERE Industry != null GROUP BY Industry
```

### Step 2: Choose the Chart Type

| Chart Type | Best For | When to Use |
|------------|----------|-------------|
| `bar` | Category comparisons | Comparing values across 3-10 categories |
| `pie` | Proportions | Showing composition with 2-5 categories |
| `doughnut` | Proportions (modern) | Like pie but with 3-6 categories |
| `line` | Trends over time | Time-series data (monthly, quarterly) |
| `horizontalBar` | Long labels | 8+ categories or categories with long names |

### Step 3: Generate the Chart

Call `generate_chart` with:
- `chart_type`: Selected chart type
- `title`: Descriptive chart title
- `labels`: Category names from the query results
- `data`: Numeric values corresponding to each label
- `dataset_label`: What the numbers represent (e.g., "Number of Leads", "Revenue ($)")

### Step 4: Present

- Show the chart to the user
- Add a brief text summary of the key insights
- Offer to drill down or change the visualization type

## Chart Examples

### Leads by Status
```
chart_type: "pie"
title: "Lead Distribution by Status"
labels: ["Open", "Contacted", "Qualified", "Converted"]
data: [45, 30, 15, 10]
dataset_label: "Number of Leads"
```

### Monthly Revenue Trend
```
chart_type: "line"
title: "Monthly Revenue (2024)"
labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
data: [50000, 65000, 45000, 80000, 72000, 95000]
dataset_label: "Revenue ($)"
```

## Tips

- Always query the data before generating a chart — never use hardcoded values
- For aggregate queries, use `COUNT(Id)`, `SUM(Amount)`, `AVG(Amount)` etc.
- If the data has only 2-5 categories, prefer `pie` or `doughnut`
- If the data has 8+ categories, prefer `horizontalBar`
- For time-series data, always use `line` chart with `ORDER BY` in the query

## References

| Document | Contents |
|----------|----------|
| [Chart Selection Guide](references/chart_selection_guide.md) | Decision matrix, SOQL patterns for charts, color palette, configuration schema |
