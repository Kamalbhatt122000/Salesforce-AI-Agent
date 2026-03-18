# Tooling API — Salesforce

## Overview

The Tooling API provides fine-grained access to Salesforce metadata for building developer tools. It supports both REST and SOAP, allows SOQL queries on metadata objects, and provides debugging capabilities.

**Base URL:**
```
{instance_url}/services/data/v62.0/tooling/
```

## Key Tooling Objects

| Object | Description |
|--------|-------------|
| `ApexClass` | Apex class definitions |
| `ApexTrigger` | Apex trigger definitions |
| `ApexComponent` | Visualforce components |
| `ApexPage` | Visualforce pages |
| `ApexLog` | Debug logs |
| `TraceFlag` | Debug log trace flags |
| `DebugLevel` | Log level configurations |
| `FlowDefinition` | Flow definitions |
| `CustomField` | Custom field metadata |
| `CustomObject` | Custom object metadata |
| `AuraDefinitionBundle` | Aura/LWC component bundles |
| `MetadataContainer` | Container for deploying metadata |
| `ContainerAsyncRequest` | Async deploy request |

## Querying Metadata via SOQL

```http
GET /services/data/v62.0/tooling/query/?q=SELECT+Id,Name,Body+FROM+ApexClass+WHERE+Name='MyClass'
```

### List All Apex Classes
```http
GET /services/data/v62.0/tooling/query/?q=SELECT+Id,Name,Status,LengthWithoutComments+FROM+ApexClass
```

### Get Apex Triggers for an Object
```http
GET /services/data/v62.0/tooling/query/?q=SELECT+Id,Name,TableEnumOrId,Body+FROM+ApexTrigger+WHERE+TableEnumOrId='Account'
```

### Get Debug Logs
```http
GET /services/data/v62.0/tooling/query/?q=SELECT+Id,LogUser.Name,Operation,DurationMilliseconds,LogLength+FROM+ApexLog+ORDER+BY+SystemModstamp+DESC+LIMIT+10
```

### Read a Specific Log
```http
GET /services/data/v62.0/tooling/sobjects/ApexLog/07Lxx0000000001/Body/
```

## Execute Anonymous Apex

Run Apex code on-the-fly without saving a class:

```http
GET /services/data/v62.0/tooling/executeAnonymous/?anonymousBody=System.debug('Hello+World');
```

**Response:**
```json
{
  "compiled": true,
  "compileProblem": null,
  "success": true,
  "exceptionMessage": null,
  "exceptionStackTrace": null,
  "line": -1,
  "column": -1
}
```

## Running Apex Tests

### Run Specific Tests
```http
POST /services/data/v62.0/tooling/runTestsAsynchronous/
Content-Type: application/json

{
  "classids": "01pxx0000000001,01pxx0000000002"
}
```

### Check Test Results
```http
GET /services/data/v62.0/tooling/query/?q=SELECT+Id,ApexClass.Name,MethodName,Outcome,Message+FROM+ApexTestResult+WHERE+AsyncApexJobId='707xx0000000001'
```

## Managing Trace Flags (Debug Logging)

### Create a Trace Flag
```http
POST /services/data/v62.0/tooling/sobjects/TraceFlag/
Content-Type: application/json

{
  "TracedEntityId": "005xx0000000001",
  "DebugLevelId": "7dlxx0000000001",
  "LogType": "USER_DEBUG",
  "StartDate": "2025-01-01T00:00:00.000Z",
  "ExpirationDate": "2025-01-02T00:00:00.000Z"
}
```

### Create a Debug Level
```http
POST /services/data/v62.0/tooling/sobjects/DebugLevel/
Content-Type: application/json

{
  "DeveloperName": "MyDebugLevel",
  "MasterLabel": "My Debug Level",
  "ApexCode": "FINEST",
  "System": "DEBUG",
  "Visualization": "NONE",
  "Database": "INFO",
  "Callout": "INFO",
  "Workflow": "INFO"
}
```

## Deploying Apex via Tooling API

### Using MetadataContainer

1. **Create a container:**
```http
POST /services/data/v62.0/tooling/sobjects/MetadataContainer/
Content-Type: application/json

{ "Name": "MyDeployContainer" }
```

2. **Add an Apex class member:**
```http
POST /services/data/v62.0/tooling/sobjects/ApexClassMember/
Content-Type: application/json

{
  "MetadataContainerId": "0Dcxx0000000001",
  "ContentEntityId": "01pxx0000000001",
  "Body": "public class MyClass { public String hello() { return 'Hello'; } }"
}
```

3. **Deploy (async):**
```http
POST /services/data/v62.0/tooling/sobjects/ContainerAsyncRequest/
Content-Type: application/json

{
  "MetadataContainerId": "0Dcxx0000000001",
  "IsCheckOnly": false
}
```

4. **Check deploy status:**
```http
GET /services/data/v62.0/tooling/sobjects/ContainerAsyncRequest/1drxx0000000001
```

## Tooling API vs Metadata API

| Feature | Tooling API | Metadata API |
|---------|-------------|--------------|
| Granularity | Individual components | Full packages (ZIP) |
| SOQL queries | Yes | No |
| Real-time editing | Yes | No (async deploy) |
| Debug logs | Yes | No |
| Best for | Dev tools, IDE, debugging | CI/CD, deployment |
