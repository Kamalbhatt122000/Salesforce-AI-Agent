# Text Analysis Reference

## Overview

The `analyze_field_data` tool enables AI-powered analysis of unstructured text data stored in Salesforce fields. Instead of relying on SOQL (which cannot perform text analysis), the tool fetches raw text values and lets the AI perform natural language analysis.

## How It Works

1. **User asks an analytical question** (e.g., "What are the top pain points from Sales Insights?")
2. **AI calls `analyze_field_data`** with the object name and field name
3. **Tool queries Salesforce** to fetch all non-null values from that field
4. **Raw text data is returned** to the AI
5. **AI analyzes the text** — extracting themes, patterns, keywords, sentiments, etc.
6. **AI presents structured findings** to the user

## Supported Analysis Types

| Analysis Type | Example Question |
|--------------|-----------------|
| Pain point extraction | "What are the top customer pain points?" |
| Theme identification | "What are the common themes in feedback?" |
| Sentiment analysis | "How do customers feel about our product?" |
| Keyword extraction | "What are the most mentioned topics?" |
| Summarization | "Summarize all sales insights" |
| Trend detection | "What patterns do you see in the descriptions?" |
| Category grouping | "Group the feedback into categories" |

## Tool Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `object_name` | Yes | Salesforce object API name (e.g., `Lead`, `Case`, `Account`) |
| `field_name` | Yes | Text field API name (e.g., `Sales_Insight__c`, `Description`) |
| `where_clause` | No | SOQL WHERE filter (without `WHERE` keyword) |
| `limit` | No | Max records to fetch (default: 200) |

## Common Text Fields by Object

| Object | Common Text Fields |
|--------|-------------------|
| Lead | `Description`, `Sales_Insight__c`, custom fields |
| Case | `Description`, `Subject`, `Comments` |
| Account | `Description`, custom fields |
| Opportunity | `Description`, `NextStep`, custom fields |
| Contact | `Description`, custom fields |

## Tips

- Use `describe_object` first if unsure which field contains the data
- Filter with `where_clause` to focus analysis (e.g., `"Status = 'Open'"`)
- Adjust `limit` based on data volume — higher for comprehensive analysis, lower for quick summaries
- The AI will automatically identify patterns, rank by frequency, and provide examples
