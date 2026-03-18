# Security & Sharing — Salesforce

## Overview

Salesforce security operates in layers: **Org-level → Object-level → Field-level → Record-level**. Each layer restricts access progressively.

---

## Org-Level Security

### Login Security
- **IP Restrictions** — limit login to specific IP ranges
- **Login Hours** — restrict login to specific time windows
- **Multi-Factor Authentication (MFA)** — required for all users
- **Password Policies** — complexity, expiration, lockout

### Trusted IPs
**Setup → Network Access** — IP ranges that skip MFA challenges.

---

## Object-Level Security (CRUD)

Controls which objects a user can Create, Read, Update, Delete.

### Profiles
- Every user has **exactly one** profile
- Profiles define baseline permissions
- Standard profiles (System Administrator, Standard User, etc.)
- Custom profiles for specific needs

### Permission Sets
- **Additional permissions** layered on top of profiles
- A user can have **multiple** permission sets
- Better practice than creating many custom profiles

### Permission Set Groups
- Bundle multiple permission sets together
- Assign a group instead of individual sets

### Object Permissions Matrix

| Permission | Description |
|-----------|-------------|
| **Read** | View records |
| **Create** | Create new records |
| **Edit** | Modify existing records |
| **Delete** | Delete records |
| **View All** | View all records (overrides sharing) |
| **Modify All** | Full access (overrides sharing + ownership) |

---

## Field-Level Security (FLS)

Controls visibility and editability of individual fields per profile/permission set.

| Setting | Effect |
|---------|--------|
| **Visible** | User can see the field |
| **Read-Only** | User can see but not edit |
| **Hidden** | Field is completely invisible |

### Set FLS via:
- **Profile → Field-Level Security**
- **Permission Set → Object Settings → Field Permissions**
- **Object Manager → Field → Set Field-Level Security**

> **Important in Apex:** By default, Apex runs in **system mode** (bypasses FLS). Use `WITH SECURITY_ENFORCED` in SOQL or `Security.stripInaccessible()` to respect FLS.

```apex
// Enforce FLS in SOQL
List<Account> accounts = [SELECT Id, Name, AnnualRevenue FROM Account WITH SECURITY_ENFORCED];

// Strip inaccessible fields
SObjectAccessDecision decision = Security.stripInaccessible(AccessType.READABLE, accounts);
List<Account> sanitized = decision.getRecords();
```

---

## Record-Level Security (Sharing)

Controls which **specific records** a user can see. Operates in layers:

### 1. Organization-Wide Defaults (OWD)

Sets the **baseline** sharing level for each object:

| Setting | Description |
|---------|-------------|
| **Private** | Only owner and users above in role hierarchy can see |
| **Public Read Only** | All users can see, only owner can edit |
| **Public Read/Write** | All users can see and edit |
| **Controlled by Parent** | Inherits sharing from master-detail parent |

**Setup → Sharing Settings → Organization-Wide Defaults**

### 2. Role Hierarchy

- Users **higher** in the hierarchy can see records owned by users **below** them
- Works like a tree: CEO → VP → Manager → Rep
- Only applies when OWD is Private or Public Read Only

### 3. Sharing Rules

Open access beyond OWD for specific groups:

**Types:**
- **Owner-based** — share records owned by Group A with Group B
- **Criteria-based** — share records matching field criteria

```
Share Accounts where Industry = 'Technology' → Read/Write to 'Tech Team' group
```

### 4. Manual Sharing
- Record owner can manually share with specific users
- **Setup → Enable Manual Sharing** on the object

### 5. Apex Managed Sharing
Programmatic sharing via `Share` objects:

```apex
AccountShare share = new AccountShare();
share.AccountId = '001xxx';
share.UserOrGroupId = '005xxx';
share.AccountAccessLevel = 'Edit';
share.RowCause = Schema.AccountShare.RowCause.Manual;
insert share;
```

---

## Sharing Model Summary

```
Most Restrictive ← OWD → Role Hierarchy → Sharing Rules → Manual Sharing → Most Open
```

Record access can only be **opened up**, never restricted below OWD.

---

## Special Permissions

| Permission | Effect |
|-----------|--------|
| **View All Data** | See all records across all objects |
| **Modify All Data** | Full CRUD on all records |
| **View All** (per object) | See all records of that object |
| **Modify All** (per object) | Full CRUD on that object's records |
| **Delegated Admin** | Manage users in specific roles |

---

## Enforce Security in Code

### In SOQL
```apex
// Enforces FLS — throws error if user can't access a field
SELECT Id, Name FROM Account WITH SECURITY_ENFORCED

// User mode — enforces CRUD and FLS
SELECT Id, Name FROM Account WITH USER_MODE
```

### In DML
```apex
// Run DML in user mode (respects CRUD/FLS)
Database.insert(accounts, AccessLevel.USER_MODE);
```

### In Apex REST
```apex
// Use WITH SECURITY_ENFORCED or stripInaccessible in all REST endpoints
```
