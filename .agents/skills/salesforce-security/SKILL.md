---
name: salesforce-security
description: Guide on Salesforce security model — profiles, permission sets, field-level security, org-wide defaults, sharing rules, role hierarchy, and record access. Use when the user asks about access control, permissions, security settings, or data visibility in Salesforce.
metadata:
  author: salesforce-ai-agent
  version: "2.0"
  category: security
  tier: 3
  dependencies:
    - salesforce-auth
---

# Salesforce Security & Sharing Skill

Understand and configure the Salesforce security model.

## Security Layers (Top to Bottom)

```
1. Organization Level  → Login IP ranges, login hours, password policies
2. Object Level        → Profiles & Permission Sets (CRUD on objects)
3. Field Level         → Field-Level Security (FLS) — visible/read-only/hidden
4. Record Level        → OWD + Role Hierarchy + Sharing Rules + Manual Sharing
```

## Organization-Wide Defaults (OWD)

| Setting | Meaning |
|---------|---------|
| **Private** | Only owner and users above in role hierarchy can see |
| **Public Read Only** | All users can see, only owner can edit |
| **Public Read/Write** | All users can see and edit |
| **Controlled by Parent** | Access determined by parent record (Master-Detail) |

## Profiles vs Permission Sets

| Profiles | Permission Sets |
|----------|----------------|
| Every user has exactly ONE | Users can have MANY |
| Set baseline permissions | Grant additional permissions |
| Control login hours, IP ranges | More granular, additive |
| Assigned at user creation | Assigned as needed |

## Role Hierarchy

- Users can **see records owned by users below them** in the hierarchy
- Does NOT restrict access — only **opens up** access
- Combined with OWD to determine visibility

## Sharing Rules

| Type | Description |
|------|-------------|
| **Ownership-Based** | Share records owned by users in Group A with Group B |
| **Criteria-Based** | Share records matching field criteria with a group |
| **Manual Sharing** | Record owner manually shares with specific users |

## Field-Level Security (FLS)

- Controls visibility and editability of individual fields
- Set per Profile or Permission Set
- Three states: **Visible**, **Read-Only**, **Hidden**
- FLS is enforced in APIs, reports, and list views

## Best Practices

- Start with the **most restrictive OWD** and open up with sharing rules
- Use **Permission Sets** instead of creating many profiles
- Regularly audit sharing rules and role hierarchy
- Use **Permission Set Groups** to bundle related permission sets
- Apply **principle of least privilege** — grant only what's needed

## References

| Document | Contents |
|----------|----------|
| [Sharing Model](references/sharing_model.md) | OWD settings, profiles vs permission sets, sharing rule types, FLS states |
