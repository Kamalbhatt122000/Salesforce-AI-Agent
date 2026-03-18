# Streaming API & Platform Events — Salesforce

## Overview

The Streaming API enables near real-time notifications when data changes in Salesforce. It uses a **publish-subscribe** model. External systems subscribe to channels and receive push notifications when events occur — no polling needed.

## Event Types

| Type | Description | Use Case |
|------|-------------|----------|
| **PushTopic** | Notifications based on SOQL query changes | Track record changes matching a query |
| **Change Data Capture (CDC)** | Detailed change notifications for objects | Sync external systems with Salesforce data |
| **Platform Events** | Custom event messages (user-defined schema) | Event-driven architecture, app-to-app messaging |
| **Generic Events** | Simple string-based notifications | Lightweight notifications |

---

## PushTopic Events

### Create a PushTopic
```apex
PushTopic pushTopic = new PushTopic();
pushTopic.Name = 'AccountUpdates';
pushTopic.Query = 'SELECT Id, Name, Industry FROM Account';
pushTopic.ApiVersion = 62.0;
pushTopic.NotifyForOperationCreate = true;
pushTopic.NotifyForOperationUpdate = true;
pushTopic.NotifyForOperationDelete = true;
pushTopic.NotifyForFields = 'Referenced';
insert pushTopic;
```

### Subscribe via CometD
Channel: `/topic/AccountUpdates`

**Event payload:**
```json
{
  "channel": "/topic/AccountUpdates",
  "data": {
    "event": { "type": "updated", "createdDate": "2025-01-15T10:30:00.000Z" },
    "sobject": { "Id": "001xxx", "Name": "Acme Corp", "Industry": "Technology" }
  }
}
```

---

## Change Data Capture (CDC)

CDC delivers detailed change events for standard and custom objects.

### Enable CDC
**Setup → Change Data Capture → Select Objects**

### Subscribe
Channel pattern: `/data/<ObjectName>ChangeEvent`

Example: `/data/AccountChangeEvent`

**Event payload:**
```json
{
  "data": {
    "schema": "...",
    "payload": {
      "ChangeEventHeader": {
        "entityName": "Account",
        "changeType": "UPDATE",
        "changedFields": ["Phone", "Industry"],
        "recordIds": ["001xxx"]
      },
      "Phone": "555-9999",
      "Industry": "Finance"
    }
  }
}
```

### Change Types
- `CREATE` — New record
- `UPDATE` — Record modified
- `DELETE` — Record deleted
- `UNDELETE` — Record restored from recycle bin
- `GAP_CREATE`, `GAP_UPDATE`, etc. — Events after reconnection

---

## Platform Events

Custom events with user-defined fields. They are the most flexible event type.

### Define a Platform Event
**Setup → Platform Events → New Platform Event**

- **Label:** `Order_Event__e`
- **Fields:**
  - `Order_Id__c` (Text)
  - `Status__c` (Text)
  - `Amount__c` (Number)

### Publish from Apex
```apex
Order_Event__e event = new Order_Event__e(
    Order_Id__c = 'ORD-001',
    Status__c = 'Shipped',
    Amount__c = 1500.00
);
Database.SaveResult sr = EventBus.publish(event);
if (sr.isSuccess()) {
    System.debug('Event published successfully');
}
```

### Publish via REST API
```http
POST /services/data/v62.0/sobjects/Order_Event__e/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "Order_Id__c": "ORD-001",
  "Status__c": "Shipped",
  "Amount__c": 1500.00
}
```

### Subscribe from Apex Trigger
```apex
trigger OrderEventTrigger on Order_Event__e (after insert) {
    for (Order_Event__e event : Trigger.New) {
        System.debug('Order: ' + event.Order_Id__c + ' Status: ' + event.Status__c);
        // Process the event
    }
}
```

### Subscribe via CometD
Channel: `/event/Order_Event__e`

### Subscribe via Flow
Use **Platform Event-Triggered Flow** — select the platform event as the trigger.

---

## Pub/Sub API (gRPC based)

The newer, high-performance API for platform events:

**Endpoint:** `api.pubsub.salesforce.com:7443`

**Capabilities:**
- Subscribe and publish using gRPC
- Binary Avro encoding for efficiency
- Supports `replayId` for replaying missed events
- Custom and Change Data Capture events

### Key Concepts
- **Topic:** `/event/Order_Event__e` or `/data/AccountChangeEvent`
- **Replay ID:** Resume from a specific event (useful after disconnects)
- **Replay Preset:** `LATEST` (new events only) or `EARLIEST` (all retained events)

---

## CometD Subscription (JavaScript Example)

```javascript
const cometd = new CometD();
cometd.configure({
    url: instanceUrl + '/cometd/62.0',
    requestHeaders: { Authorization: 'Bearer ' + accessToken }
});

cometd.handshake(function(handshake) {
    if (handshake.successful) {
        cometd.subscribe('/topic/AccountUpdates', function(message) {
            console.log('Event received:', message.data);
        });
    }
});
```

---

## Limits

| Limit | Value |
|-------|-------|
| Max PushTopics per org | 100 |
| Max CDC subscriptions | 2,000 events/hour (Developer), varies by edition |
| Platform Event daily allocation | Based on edition (25,000 for Enterprise) |
| Max subscribers per channel | Based on edition |
| Event retention | 72 hours (Platform Events), 3 days (CDC) |
