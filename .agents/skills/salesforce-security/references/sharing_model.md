# Security & Sharing — Sharing Model Reference

## Security Layers (Top → Bottom)

```
1. Organization Level  → Login IP ranges, login hours, password policies
2. Object Level        → Profiles & Permission Sets (CRUD on objects)
3. Field Level         → Field-Level Security (FLS) — visible/read-only/hidden
4. Record Level        → OWD + Role Hierarchy + Sharing Rules + Manual Sharing
```

## Organization-Wide Defaults (OWD)

| Setting | Who Can See | Who Can Edit |
|---------|------------|-------------|
| **Private** | Owner + users above in role hierarchy | Owner only |
| **Public Read Only** | All users | Owner only |
| **Public Read/Write** | All users | All users |
| **Controlled by Parent** | Determined by parent record | Determined by parent record |

## Profiles vs Permission Sets

| Aspect | Profiles | Permission Sets |
|--------|----------|----------------|
| Assignment | Exactly **one** per user | **Many** per user |
| Purpose | Baseline permissions | Additional permissions |
| Can restrict? | Yes (reduces access) | No (only additive) |
| Controls | Login hours, IP ranges, page layouts | Object/field/tab access |
| Best practice | Use few, generic profiles | Use many, granular perm sets |

## Permission Set Groups

Bundle related Permission Sets for easier assignment:

```
Sales Rep Group = Sales Console PS + Lead Management PS + Report Viewer PS
```

## Role Hierarchy

- Users can see records owned by users **below them**
- Does **NOT** restrict access — only **opens up** access
- Combined with OWD to determine visibility
- Maximum depth: 500 levels (recommended: < 10)

## Sharing Rules Matrix

| OWD Setting | Sharing Rule Needed? | Options |
|-------------|---------------------|---------|
| Private | Yes — to open access | Ownership-based, Criteria-based |
| Public Read Only | Optional — for edit access | Ownership-based, Criteria-based |
| Public Read/Write | No — already open | Not applicable |

## Sharing Rule Types

| Type | Description | Example |
|------|-------------|---------|
| **Ownership-Based** | Share records owned by Group A with Group B | "Share all leads owned by West Team with East Team" |
| **Criteria-Based** | Share records matching field conditions | "Share all accounts with Industry = 'Tech' with All Users" |
| **Manual Sharing** | Owner shares individual records | "Share this opportunity with my manager" |
| **Apex Managed** | Programmatic sharing via Apex | For complex, custom sharing logic |

## Field-Level Security (FLS)

Three states per field per profile/permission set:

| State | Can See? | Can Edit? |
|-------|----------|-----------|
| **Visible** | ✅ | ✅ |
| **Read-Only** | ✅ | ❌ |
| **Hidden** | ❌ | ❌ |

> **Important**: FLS is enforced in APIs, reports, list views, and search results.

## Best Practices

1. Start with the **most restrictive OWD** and open up with sharing rules
2. Use **Permission Sets** (not extra profiles) for granular access
3. Regularly **audit** role hierarchy and sharing rules
4. Apply the **principle of least privilege** — grant only what's needed
5. Use **Permission Set Groups** to reduce assignment complexity
6. Document all sharing rules with business justification
