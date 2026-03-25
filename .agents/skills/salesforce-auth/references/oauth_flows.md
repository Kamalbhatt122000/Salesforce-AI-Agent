# Salesforce Authentication — Reference

## OAuth 2.0 Flows

| Flow | Use Case | Requires Connected App |
|------|----------|----------------------|
| **Username-Password** | Server-to-server integration | Yes |
| **SOAP Login** | Simple automation scripts | No |
| **Web Server (Authorization Code)** | Web apps with user login | Yes |
| **JWT Bearer** | Headless apps, CI/CD | Yes |
| **Device Flow** | CLI tools, IoT devices | Yes |
| **Refresh Token** | Long-lived sessions | Yes |

## SOAP Login (No Connected App Required)

The simplest authentication method. Uses SOAP API to exchange username + password + security token for a session ID.

**Endpoint**: `https://login.salesforce.com/services/Soap/u/62.0`

**Request**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:urn="urn:partner.soap.sforce.com">
  <soapenv:Body>
    <urn:login>
      <urn:username>user@example.com</urn:username>
      <urn:password>MyPassword+SecurityToken</urn:password>
    </urn:login>
  </soapenv:Body>
</soapenv:Envelope>
```

## Getting Your Security Token

1. Log in to Salesforce
2. Go to **Settings** → **My Personal Information** → **Reset My Security Token**
3. Click **Reset Security Token**
4. Check your email for the new token

> **Note**: If your org has "IP Relaxation" enabled, you may not need a security token.

## Environment Variables

```
SF_USERNAME=<your-username>
SF_PASSWORD=<your-password>
SF_SECURITY_TOKEN=<your-security-token>
SF_CLIENT_ID=<connected-app-client-id>
SF_CLIENT_SECRET=<connected-app-client-secret>
SF_LOGIN_URL=https://login.salesforce.com
```

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `INVALID_LOGIN` | Wrong credentials | Verify username, password, and security token |
| `LOGIN_MUST_USE_SECURITY_TOKEN` | Missing token | Append security token to password, or whitelist your IP |
| `API_DISABLED_FOR_ORG` | API not enabled | Enable API access in Setup → User Profiles |
| `UNABLE_TO_LOCK_ROW` | Concurrent access | Retry after a moment |
| `REQUEST_LIMIT_EXCEEDED` | Too many API calls | Check API usage in Setup → System Overview |
| `INVALID_SESSION_ID` | Token expired | Re-authenticate to get a new access token |

## Connected App Setup (for OAuth 2.0)

1. Go to **Setup** → **App Manager** → **New Connected App**
2. Enable OAuth Settings
3. Select scopes: `full`, `refresh_token`, `api`
4. Set callback URL: `https://login.salesforce.com/services/oauth2/callback`
5. Save and note the **Consumer Key** and **Consumer Secret**
