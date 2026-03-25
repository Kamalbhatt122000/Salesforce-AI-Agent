# Chart Selection Guide

## Decision Matrix

| Data Characteristics | Recommended Chart | Why |
|---------------------|-------------------|-----|
| 2–5 categories showing composition | **Pie** | Clear proportional view |
| 3–6 categories showing composition | **Doughnut** | Modern pie alternative |
| 3–10 categories comparing values | **Bar** | Easy magnitude comparison |
| 8+ categories or long labels | **Horizontal Bar** | Labels fit better horizontally |
| Time-series data (sequential) | **Line** | Shows trends over time |

## Chart Types

### Bar Chart
- **Best for**: Comparing values across categories
- **Data**: 3–10 discrete categories
- **Example**: Leads per source, accounts per industry

### Pie Chart
- **Best for**: Showing composition / proportions
- **Data**: 2–5 categories
- **Example**: Lead status distribution, case priority breakdown

### Doughnut Chart
- **Best for**: Modern proportional display
- **Data**: 3–6 categories
- **Example**: Opportunity stage distribution

### Line Chart
- **Best for**: Trends over time
- **Data**: Sequential / time-ordered values
- **Example**: Monthly revenue, weekly case creation

### Horizontal Bar Chart
- **Best for**: Many categories or long labels
- **Data**: 8+ categories
- **Example**: Opportunities by stage name, accounts by full industry name

## SOQL Patterns for Charts

```sql
-- Pie/Bar: Leads by status
SELECT Status, COUNT(Id) cnt FROM Lead GROUP BY Status

-- Doughnut: Opportunities by stage
SELECT StageName, COUNT(Id) cnt FROM Opportunity GROUP BY StageName

-- Line: Monthly revenue trend
SELECT CALENDAR_MONTH(CloseDate) month, SUM(Amount) total
FROM Opportunity WHERE IsWon = true
GROUP BY CALENDAR_MONTH(CloseDate) ORDER BY CALENDAR_MONTH(CloseDate)

-- Horizontal Bar: Accounts by industry
SELECT Industry, COUNT(Id) cnt FROM Account WHERE Industry != null GROUP BY Industry

-- Bar: Cases by priority
SELECT Priority, COUNT(Id) cnt FROM Case GROUP BY Priority
```

## Chart Configuration Schema

```json
{
  "chart_type": "bar | pie | doughnut | line | horizontalBar",
  "title": "Descriptive Chart Title",
  "labels": ["Label1", "Label2", "Label3"],
  "data": [45, 30, 25],
  "dataset_label": "What the numbers represent"
}
```

## Color Palette

Charts automatically use this harmonious color palette:

| Index | Color | Hex |
|-------|-------|-----|
| 1 | Blue | `#4285F4` |
| 2 | Red | `#EA4335` |
| 3 | Yellow | `#FBBC04` |
| 4 | Green | `#34A853` |
| 5 | Purple | `#9334E6` |
| 6 | Teal | `#00ACC1` |
| 7 | Orange | `#FF6D01` |
| 8 | Pink | `#E91E63` |

## Tips

- Always query data with `GROUP BY` before generating a chart — never hardcode values
- Use `ORDER BY` for line charts to ensure correct sequence
- For aggregate queries, use `COUNT(Id)`, `SUM(Amount)`, `AVG(Amount)` etc.
- If data has only 2–5 categories, prefer `pie` or `doughnut`
- If data has 8+ categories, always use `horizontalBar`
- Add a descriptive `dataset_label` (e.g., "Number of Leads", "Revenue ($)")
