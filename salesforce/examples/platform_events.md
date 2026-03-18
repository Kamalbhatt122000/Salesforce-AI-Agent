# Example: Platform Events

Publishing and subscribing to Salesforce Platform Events.

---

## 1. Define a Platform Event

In Salesforce Setup:
1. Go to **Setup → Platform Events → New Platform Event**
2. **Label:** `Order Event`
3. **API Name:** `Order_Event__e`
4. Add fields:
   - `Order_Id__c` (Text, 50)
   - `Status__c` (Text, 50)
   - `Amount__c` (Number, 16, 2)
   - `Customer_Name__c` (Text, 100)

---

## 2. Publish from Apex

```apex
// Publish a single event
Order_Event__e event = new Order_Event__e(
    Order_Id__c = 'ORD-001',
    Status__c = 'Shipped',
    Amount__c = 1500.00,
    Customer_Name__c = 'Acme Corp'
);

Database.SaveResult sr = EventBus.publish(event);
if (sr.isSuccess()) {
    System.debug('✅ Event published: ' + event.Order_Id__c);
} else {
    for (Database.Error err : sr.getErrors()) {
        System.debug('❌ Error: ' + err.getMessage());
    }
}

// Publish multiple events
List<Order_Event__e> events = new List<Order_Event__e>();
events.add(new Order_Event__e(Order_Id__c='ORD-002', Status__c='Processing', Amount__c=750.00));
events.add(new Order_Event__e(Order_Id__c='ORD-003', Status__c='Delivered', Amount__c=2000.00));

List<Database.SaveResult> results = EventBus.publish(events);
```

---

## 3. Publish from REST API (Python)

```python
from sf_auth import SalesforceAuth
from sf_rest_client import SalesforceRESTClient

auth = SalesforceAuth(
    username="priyanka.joshi547@agentforce.com",
    password="Priyanka21#",
    security_token="vHnao3amdKeuFFObAVVuqmluH",
)
auth.authenticate_simple()

client = SalesforceRESTClient(auth)

# Publish an event via REST API
event_id = client.create("Order_Event__e", {
    "Order_Id__c": "ORD-004",
    "Status__c": "Shipped",
    "Amount__c": 3500.00,
    "Customer_Name__c": "Beta Inc"
})
print(f"Event published: {event_id}")
```

---

## 4. Subscribe with Apex Trigger

```apex
trigger OrderEventTrigger on Order_Event__e (after insert) {
    List<Task> tasksToCreate = new List<Task>();
    
    for (Order_Event__e event : Trigger.New) {
        System.debug('📦 Order Event Received:');
        System.debug('   Order: ' + event.Order_Id__c);
        System.debug('   Status: ' + event.Status__c);
        System.debug('   Amount: ' + event.Amount__c);
        
        // Create a follow-up task for shipped orders
        if (event.Status__c == 'Shipped') {
            tasksToCreate.add(new Task(
                Subject = 'Follow up on order ' + event.Order_Id__c,
                Description = 'Order shipped for ' + event.Customer_Name__c + 
                             '. Amount: $' + event.Amount__c,
                Status = 'Not Started',
                Priority = 'Normal'
            ));
        }
    }
    
    if (!tasksToCreate.isEmpty()) {
        insert tasksToCreate;
    }
}
```

---

## 5. Subscribe with Flow

1. Go to **Setup → Flows → New Flow**
2. Select **Platform Event-Triggered Flow**
3. Choose `Order_Event__e` as the platform event
4. Add conditions: e.g., `{!$Record.Status__c} = 'Shipped'`
5. Add actions: Create Task, Send Email, Update Records, etc.

---

## 6. Subscribe with CometD (JavaScript)

```javascript
// Using CometD library
const cometd = new CometD();

cometd.configure({
    url: instanceUrl + '/cometd/62.0',
    requestHeaders: { Authorization: 'Bearer ' + accessToken }
});

cometd.handshake(function(handshake) {
    if (handshake.successful) {
        console.log('✅ Connected to Salesforce streaming');
        
        cometd.subscribe('/event/Order_Event__e', function(message) {
            const event = message.data.payload;
            console.log('📦 Order Event:', {
                orderId: event.Order_Id__c,
                status: event.Status__c,
                amount: event.Amount__c,
                customer: event.Customer_Name__c
            });
        });
    }
});
```

---

## Event Replay

Platform Events are retained for **72 hours**. Use `replayId` to replay missed events:

```javascript
// Subscribe from a specific replay ID
cometd.subscribe('/event/Order_Event__e', callback, {
    ext: { replay: { '/event/Order_Event__e': -2 } }  // -2 = all retained events
});
// -1 = new events only
// -2 = all retained events
// <specific_id> = events after that ID
```
