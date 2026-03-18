# Authentication — Salesforce API Access

## Overview

Every Salesforce API call requires authentication. Salesforce uses **OAuth 2.0** as its primary authentication mechanism. You must obtain an **access token** before making any API request.

## Authentication Methods

### 1. Username-Password Flow (Simplest)

Best for: server-to-server integrations, scripts, testing.

**Request:**
```http
POST https://login.salesforce.com/services/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=password
&client_id=<CONNECTED_APP_CLIENT_ID>
&client_secret=<CONNECTED_APP_CLIENT_SECRET>
&username=<USERNAME>
&password=<PASSWORD><SECURITY_TOKEN>
```

> **Important:** The password field is `password + security_token` concatenated together (no separator).

**Response:**
```json
{
  "access_token": "00D...",
  "instance_url": "https://yourorg.my.salesforce.com",
  "id": "https://login.salesforce.com/id/00D.../005...",
  "token_type": "Bearer",
  "issued_at": "1679500000000",
  "signature": "..."
}
```

Use `access_token` in every subsequent API call:
```
Authorization: Bearer <access_token>
```

Use `instance_url` as the base URL for all API calls.

### 2. Web Server Flow (OAuth 2.0 Authorization Code)

Best for: web applications where a user logs in interactively.

**Step 1 — Redirect user to authorize:**
```
https://login.salesforce.com/services/oauth2/authorize
  ?response_type=code
  &client_id=<CONNECTED_APP_CLIENT_ID>
  &redirect_uri=<CALLBACK_URL>
  &scope=api refresh_token
```

**Step 2 — Exchange code for token:**
```http
POST https://login.salesforce.com/services/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=<AUTH_CODE>
&client_id=<CONNECTED_APP_CLIENT_ID>
&client_secret=<CONNECTED_APP_CLIENT_SECRET>
&redirect_uri=<CALLBACK_URL>
```

### 3. JWT Bearer Token Flow

Best for: server-to-server without user interaction, CI/CD pipelines.

**Steps:**
1. Create an X.509 certificate and upload to Connected App
2. Build a JWT with claims: `iss` (client_id), `sub` (username), `aud` (login URL), `exp` (expiration)
3. Sign the JWT with your private key
4. Exchange for access token:

```http
POST https://login.salesforce.com/services/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
&assertion=<SIGNED_JWT>
```

### 4. Refresh Token Flow

When you have a `refresh_token` from a prior auth:

```http
POST https://login.salesforce.com/services/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&client_id=<CONNECTED_APP_CLIENT_ID>
&client_secret=<CONNECTED_APP_CLIENT_SECRET>
&refresh_token=<REFRESH_TOKEN>
```

## Connected App Setup

To use any OAuth flow, you need a **Connected App** in Salesforce:

1. Go to **Setup → App Manager → New Connected App**
2. Enable **OAuth Settings**
3. Set **Callback URL** (e.g., `https://localhost/callback` for testing)
4. Select **OAuth Scopes**:
   - `api` — Access and manage data
   - `refresh_token` — Perform requests at any time
   - `full` — Full access
5. Save and note the **Consumer Key** (Client ID) and **Consumer Secret**

## Login URLs

| Environment | Login URL |
|-------------|-----------|
| Production / Developer | `https://login.salesforce.com` |
| Sandbox | `https://test.salesforce.com` |
| My Domain | `https://yourdomain.my.salesforce.com` |

## Session Management

- Access tokens expire (default: ~2 hours; configurable in Connected App)
- Use `refresh_token` to get new access tokens without re-authentication
- Revoke tokens: `POST https://login.salesforce.com/services/oauth2/revoke?token=<TOKEN>`

## Security Best Practices

- **Never hardcode credentials** in source code
- Use environment variables or secure vaults
- Restrict Connected App IP ranges in production
- Enable **IP Relaxation** only for trusted apps
- Use the **JWT flow** for automated systems (no passwords in transit)
