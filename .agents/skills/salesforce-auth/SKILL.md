---
name: salesforce-auth
description: Authenticate and connect to a Salesforce org using Username-Password flow or OAuth 2.0. Use when the user asks about connecting to Salesforce, setting up credentials, troubleshooting authentication issues, or managing Connected Apps and security tokens.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: foundation
  tier: 0
  dependencies: []
---

# Salesforce Authentication Skill

Set up and manage Salesforce org authentication.

## Prerequisites

- A Salesforce org (Developer, Sandbox, or Production)
- Credentials: **Username**, **Password**, **Security Token**
- Python 3.8+ with `requests` library

## Credential Configuration

Set these environment variables in your `.env` file:

```
SF_USERNAME=<your-username>
SF_PASSWORD=<your-password>
SF_SECURITY_TOKEN=<your-security-token>
```

## Authentication Methods

### 1. Username-Password Flow (Simple)

The simplest method. Uses username + password + security token.

```python
from sf_auth import SalesforceAuth

auth = SalesforceAuth(
    username="user@example.com",
    password="MyPassword",
    security_token="XXXXXXXXXX"
)
auth.authenticate_simple()
# auth.instance_url → "https://yourorg.my.salesforce.com"
# auth.access_token → "00D..."
```

### 2. OAuth 2.0 (Connected App)

For production integrations. Requires a Connected App in Salesforce Setup.

**Additional env vars:**
```
SF_CLIENT_ID=<connected-app-client-id>
SF_CLIENT_SECRET=<connected-app-client-secret>
SF_LOGIN_URL=https://login.salesforce.com
```

## Getting Your Security Token

1. Log in to Salesforce
2. Go to **Settings** → **My Personal Information** → **Reset My Security Token**
3. Click **Reset Security Token**
4. Check your email for the new token

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `INVALID_LOGIN` | Check username, password, and security token |
| `LOGIN_MUST_USE_SECURITY_TOKEN` | Append security token to password or add your IP to trusted ranges |
| `API_DISABLED_FOR_ORG` | Enable API access in the org settings |
| `UNABLE_TO_LOCK_ROW` | Retry after a moment — concurrent operations on the same record |

## Scripts

| Script | Purpose |
|--------|---------|
| [sf_auth.py](scripts/sf_auth.py) | OAuth 2.0 authentication & token generation |

## References

| Document | Contents |
|----------|----------|
| [OAuth Flows](references/oauth_flows.md) | All authentication methods, Connected App setup, troubleshooting |
