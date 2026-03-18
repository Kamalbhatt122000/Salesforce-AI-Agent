---
name: salesforce
description: Complete Salesforce platform capabilities — all APIs (REST, SOAP, Bulk, Metadata, Tooling, Streaming), SOQL/SOSL queries, Apex development, Flows & automation, security model, objects, reports, and governor limits. Includes Python helper scripts for direct Salesforce org interaction.
---

# Salesforce Platform Skill

This skill gives you comprehensive knowledge and tools to interact with the Salesforce platform. It covers every major API, query language, development framework, automation tool, and operational constraint.

## Quick Start

1. **Authenticate** — Read `instructions/01_authentication.md` to set up OAuth 2.0 tokens
2. **Query Data** — Read `instructions/08_soql_sosl.md` for SOQL/SOSL syntax
3. **Call APIs** — Read `instructions/02_rest_api.md` for the most common API
4. **Run Scripts** — Use `scripts/sf_auth.py` + `scripts/sf_rest_client.py` for programmatic access

## Prerequisites

- A Salesforce org (Developer, Sandbox, or Production)
- Credentials: **Username**, **Password**, **Security Token**
- For API access: a **Connected App** with OAuth 2.0 enabled
- Python 3.8+ with `requests` library (for scripts)

## Credential Configuration

Set these environment variables before using the scripts:

```
SF_USERNAME=<your-username>
SF_PASSWORD=<your-password>
SF_SECURITY_TOKEN=<your-security-token>
SF_CLIENT_ID=<connected-app-client-id>
SF_CLIENT_SECRET=<connected-app-client-secret>
SF_LOGIN_URL=https://login.salesforce.com
```

Or use the Username-Password flow directly with the provided credentials.

## Module Index

### Instruction Modules (`instructions/`)

| # | Module | What You'll Learn |
|---|--------|-------------------|
| 01 | [Authentication](instructions/01_authentication.md) | OAuth 2.0 flows, Connected Apps, token management |
| 02 | [REST API](instructions/02_rest_api.md) | CRUD, Composite API, sObject endpoints, pagination |
| 03 | [SOAP API](instructions/03_soap_api.md) | WSDL, Enterprise/Partner API, login(), describeSObject |
| 04 | [Bulk API](instructions/04_bulk_api.md) | Bulk API 2.0, jobs, CSV uploads, large-data operations |
| 05 | [Metadata API](instructions/05_metadata_api.md) | Deploy, retrieve, CI/CD, metadata types |
| 06 | [Tooling API](instructions/06_tooling_api.md) | Apex management, logs, debug, executeAnonymous |
| 07 | [Streaming API](instructions/07_streaming_api.md) | PushTopics, CDC, Platform Events, Pub/Sub |
| 08 | [SOQL & SOSL](instructions/08_soql_sosl.md) | Query syntax, relationships, aggregates, search |
| 09 | [Apex Development](instructions/09_apex_development.md) | Classes, triggers, async Apex, test classes |
| 10 | [Flows & Automation](instructions/10_flows_automation.md) | Screen Flows, Record-Triggered, Scheduled flows |
| 11 | [Objects & Fields](instructions/11_objects_and_fields.md) | Standard/Custom objects, field types, relationships |
| 12 | [Reports & Dashboards](instructions/12_reports_dashboards.md) | Analytics API, report types, dashboard refresh |
| 13 | [Security & Sharing](instructions/13_security_sharing.md) | Profiles, Permission Sets, OWD, Sharing Rules |
| 14 | [Governor Limits](instructions/14_governor_limits.md) | All Apex, API, SOQL, DML limits |

### Helper Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| [sf_auth.py](scripts/sf_auth.py) | OAuth 2.0 authentication & token generation |
| [sf_rest_client.py](scripts/sf_rest_client.py) | Generic REST API client for any Salesforce endpoint |
| [sf_bulk_client.py](scripts/sf_bulk_client.py) | Bulk API 2.0 job management |
| [sf_query.py](scripts/sf_query.py) | SOQL/SOSL query execution with auto-pagination |

### Examples (`examples/`)

- [CRUD Operations](examples/crud_operations.md) — Create, Read, Update, Delete records
- [Bulk Data Load](examples/bulk_data_load.md) — Loading 100k+ records via Bulk API
- [Query Patterns](examples/query_patterns.md) — Common SOQL patterns & relationship queries
- [Apex REST Service](examples/apex_rest_service.md) — Building custom Apex REST endpoints
- [Platform Events](examples/platform_events.md) — Publishing & subscribing to events
- [Metadata Deployment](examples/metadata_deployment.md) — Deploy metadata between orgs

### Resources (`resources/`)

- [API Reference URLs](resources/api_reference_urls.md) — Official Salesforce documentation links
- [Error Codes](resources/error_codes.md) — Common error codes & fixes
- [Governor Limits Table](resources/governor_limits_table.md) — Quick-reference limits
- [Object Model Cheatsheet](resources/object_model_cheatsheet.md) — Standard objects & relationships

## When to Use Which API

| Scenario | Recommended API |
|----------|----------------|
| Simple CRUD on a few records | REST API |
| Complex enterprise integration | SOAP API |
| Loading/extracting 2,000+ records | Bulk API 2.0 |
| Real-time data change notifications | Streaming API |
| Deploy configuration between orgs | Metadata API |
| Build developer tools, access Apex logs | Tooling API |
| Custom query on known objects | SOQL |
| Full-text keyword search across objects | SOSL |
