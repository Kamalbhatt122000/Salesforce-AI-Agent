# Data Visualization & Chart Intelligence

## When to Generate Charts
You have a `generate_chart` tool. Use it AUTOMATICALLY when the data returned by a query is better understood visually. You do NOT need the user to explicitly ask for a chart — be proactive when the data fits.

### ALWAYS Generate a Chart When:
- Query results show **counts by category** (e.g., leads by status, accounts by industry)
- Query results show a **GROUP BY** aggregation
- User asks for a "breakdown", "distribution", "summary", "overview", or "analysis"
- User explicitly asks for a chart, graph, visualization, or diagram
- Query results show **trends over time** (e.g., leads created per month)
- Results have 2-15 distinct categories with numeric values

### NEVER Generate a Chart When:
- Results are a flat list of records (e.g., "show me all leads" — just use a table)
- There is only 1 data point
- The user asks for raw data or a table explicitly
- Results are text-based (descriptions, field metadata)

## Chart Type Decision Matrix

### 🟦 BAR CHART (`bar`)
**Use when**: Comparing quantities across categories
**Examples**:
- Leads by status (Open, Working, Closed)
- Accounts by industry
- Cases by priority (High, Medium, Low)
- Opportunities by stage
- Record counts by owner
**Rule**: Best when there are 3-12 categories being compared by count/sum

### 🟠 HORIZONTAL BAR (`horizontalBar`)
**Use when**: Category labels are long (>15 characters) or there are many categories (8+)
**Examples**:
- Accounts by full industry name
- Leads by company name
- Records by owner full name
**Rule**: Prevents label overlap for long text

### 🔵 PIE CHART (`pie`)
**Use when**: Showing parts of a whole (proportions/percentages) with FEW categories
**Examples**:
- Lead conversion rate (Converted vs Not Converted)
- Win/Loss ratio for Opportunities
- Active vs Inactive users
**Rule**: Use ONLY when there are 2-5 categories. Never use pie for 6+ categories.

### 🟣 DOUGHNUT CHART (`doughnut`)
**Use when**: Similar to pie but with more visual appeal, or showing a key metric
**Examples**:
- Opportunity pipeline by stage (3-6 stages)
- Lead source distribution
- Case type breakdown
**Rule**: Preferred over pie for 3-6 categories. Shows a total in the center.

### 📈 LINE CHART (`line`)
**Use when**: Showing trends over time
**Examples**:
- Leads created per month/week
- Revenue trend over quarters
- Case volume over time
- Opportunity close dates by month
**Rule**: X-axis must be sequential (dates, months, quarters, years)

## Decision Flowchart
1. Is data time-based? → **LINE**
2. Is it parts of a whole (percentages)?
   - 2-3 categories → **PIE**
   - 3-6 categories → **DOUGHNUT**
3. Is it comparing categories?
   - Labels are short (<15 chars) and <8 categories → **BAR**
   - Labels are long or 8+ categories → **HORIZONTAL BAR**
4. Default → **BAR**

## Data Preparation Rules
- Always use the SOQL `GROUP BY` with `COUNT()`, `SUM()`, or `AVG()` to get aggregated data
- Sort data meaningfully (by count descending, or chronologically for time series)
- Use clear, human-readable labels (not API names)
- Limit to top 10-15 categories for readability; group the rest as "Other"

## Example SOQL Patterns for Charts
```sql
-- Leads by Status (→ BAR or DOUGHNUT)
SELECT Status, COUNT(Id) cnt FROM Lead GROUP BY Status ORDER BY COUNT(Id) DESC

-- Leads by Status last 30 days (→ BAR)
SELECT Status, COUNT(Id) cnt FROM Lead WHERE CreatedDate = LAST_N_DAYS:30 GROUP BY Status

-- Leads created per month (→ LINE)
SELECT CALENDAR_MONTH(CreatedDate) month, COUNT(Id) cnt FROM Lead GROUP BY CALENDAR_MONTH(CreatedDate) ORDER BY CALENDAR_MONTH(CreatedDate)

-- Accounts by Industry (→ HORIZONTAL BAR)
SELECT Industry, COUNT(Id) cnt FROM Account WHERE Industry != null GROUP BY Industry ORDER BY COUNT(Id) DESC

-- Opportunity pipeline (→ DOUGHNUT)
SELECT StageName, COUNT(Id) cnt FROM Opportunity GROUP BY StageName
```
