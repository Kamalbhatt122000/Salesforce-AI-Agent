# Metadata API — Salesforce

## Overview

The Metadata API manages org **configuration and customization** (not data). It deploys, retrieves, creates, and deletes metadata components like custom objects, fields, page layouts, Apex classes, Flows, and more.

**Primary use:** Moving configurations between orgs (sandbox → production), CI/CD pipelines, and programmatic org setup.

## Key Operations

### listMetadata
Lists metadata components of a given type:
```xml
<listMetadata>
  <queries>
    <type>CustomObject</type>
  </queries>
</listMetadata>
```

Returns: `fullName`, `type`, `lastModifiedDate`, `createdById`, etc.

### describeMetadata
Returns available metadata types and organization info:
```xml
<describeMetadata>
  <apiVersion>62.0</apiVersion>
</describeMetadata>
```

### retrieve
Retrieves metadata components as a ZIP file:
```xml
<retrieve>
  <retrieveRequest>
    <apiVersion>62.0</apiVersion>
    <unpackaged>
      <types>
        <members>Account</members>
        <members>Contact</members>
        <name>CustomObject</name>
      </types>
      <types>
        <members>MyApexClass</members>
        <name>ApexClass</name>
      </types>
      <version>62.0</version>
    </unpackaged>
  </retrieveRequest>
</retrieve>
```

**Check status:**
```xml
<checkRetrieveStatus>
  <asyncProcessId>09Sxx0000000001</asyncProcessId>
</checkRetrieveStatus>
```

### deploy
Deploys a ZIP file containing metadata:
```xml
<deploy>
  <ZipFile>BASE64_ENCODED_ZIP</ZipFile>
  <DeployOptions>
    <checkOnly>false</checkOnly>
    <runTests>MyTestClass</runTests>
    <testLevel>RunSpecifiedTests</testLevel>
  </DeployOptions>
</deploy>
```

**Test Levels:**
| Value | Meaning |
|-------|---------|
| `NoTestRun` | Skip tests (sandbox only) |
| `RunSpecifiedTests` | Run named test classes |
| `RunLocalTests` | Run all local tests (no managed package tests) |
| `RunAllTestsInOrg` | Run every test |

**Check deploy status:**
```xml
<checkDeployStatus>
  <asyncProcessId>0Afxx0000000001</asyncProcessId>
  <includeDetails>true</includeDetails>
</checkDeployStatus>
```

### createMetadata / updateMetadata / deleteMetadata
Operate on individual metadata components without ZIP:

```xml
<createMetadata>
  <metadata xsi:type="CustomField">
    <fullName>Account.MyField__c</fullName>
    <label>My Field</label>
    <type>Text</type>
    <length>100</length>
  </metadata>
</createMetadata>
```

---

## Common Metadata Types

| Type | Description |
|------|-------------|
| `CustomObject` | Custom and standard objects |
| `CustomField` | Fields on objects |
| `ApexClass` | Apex classes |
| `ApexTrigger` | Apex triggers |
| `Flow` | Flow definitions |
| `Layout` | Page layouts |
| `Profile` | User profiles |
| `PermissionSet` | Permission sets |
| `ValidationRule` | Validation rules |
| `WorkflowRule` | Workflow rules (legacy) |
| `CustomTab` | Custom tabs |
| `StaticResource` | Static resources (JS, CSS, images) |
| `LightningComponentBundle` | LWC components |
| `AuraDefinitionBundle` | Aura components |

---

## Package.xml Structure

The manifest file that defines what to deploy/retrieve:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>*</members>
    <name>ApexClass</name>
  </types>
  <types>
    <members>Account</members>
    <name>CustomObject</name>
  </types>
  <types>
    <members>Account.MyField__c</members>
    <name>CustomField</name>
  </types>
  <version>62.0</version>
</Package>
```

Use `*` as member to include all components of that type.

---

## REST-Based Metadata (Alternative)

You can also use REST for metadata operations:

### Deploy via REST
```http
POST /services/data/v62.0/metadata/deployRequest
Content-Type: multipart/form-data
```

### Retrieve via REST
```http
POST /services/data/v62.0/metadata/retrieveRequest
```

---

## Best Practices

- Always **validate before deploying** (`checkOnly: true`)
- Use `RunLocalTests` for production deployments
- Version-control your `package.xml` and metadata files
- Use **Salesforce DX (sfdx/sf CLI)** for modern source-driven development
- Monitor deploy status — large deploys can take minutes
