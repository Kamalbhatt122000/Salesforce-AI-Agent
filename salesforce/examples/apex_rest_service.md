# Example: Custom Apex REST Service

Build a custom REST API endpoint in Salesforce using Apex.

---

## Apex Class

```apex
@RestResource(urlMapping='/accounts/*')
global class AccountRestService {
    
    // GET /services/apexrest/accounts/<accountId>
    @HttpGet
    global static Account getAccount() {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substringAfterLast('/');
        
        return [
            SELECT Id, Name, Industry, Phone, Website, AnnualRevenue,
                   (SELECT Id, FirstName, LastName, Email FROM Contacts LIMIT 5)
            FROM Account
            WHERE Id = :accountId
        ];
    }
    
    // POST /services/apexrest/accounts/
    @HttpPost
    global static String createAccount(String name, String industry, String phone) {
        Account acc = new Account(
            Name = name,
            Industry = industry,
            Phone = phone
        );
        insert acc;
        return acc.Id;
    }
    
    // PATCH /services/apexrest/accounts/<accountId>
    @HttpPatch
    global static Account updateAccount() {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substringAfterLast('/');
        
        // Parse the request body
        Map<String, Object> params = (Map<String, Object>) JSON.deserializeUntyped(req.requestBody.toString());
        
        Account acc = [SELECT Id FROM Account WHERE Id = :accountId];
        
        if (params.containsKey('name'))     acc.Name = (String) params.get('name');
        if (params.containsKey('industry')) acc.Industry = (String) params.get('industry');
        if (params.containsKey('phone'))    acc.Phone = (String) params.get('phone');
        
        update acc;
        return acc;
    }
    
    // DELETE /services/apexrest/accounts/<accountId>
    @HttpDelete
    global static void deleteAccount() {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substringAfterLast('/');
        
        Account acc = [SELECT Id FROM Account WHERE Id = :accountId];
        delete acc;
    }
}
```

---

## Test Class

```apex
@isTest
public class AccountRestServiceTest {
    
    @TestSetup
    static void setup() {
        Account acc = new Account(Name = 'Test Account', Industry = 'Technology', Phone = '555-1234');
        insert acc;
    }
    
    @isTest
    static void testGetAccount() {
        Account acc = [SELECT Id FROM Account LIMIT 1];
        
        RestRequest req = new RestRequest();
        req.requestURI = '/services/apexrest/accounts/' + acc.Id;
        req.httpMethod = 'GET';
        RestContext.request = req;
        
        Test.startTest();
        Account result = AccountRestService.getAccount();
        Test.stopTest();
        
        System.assertEquals('Test Account', result.Name);
    }
    
    @isTest
    static void testCreateAccount() {
        Test.startTest();
        String accountId = AccountRestService.createAccount('New Corp', 'Finance', '555-5678');
        Test.stopTest();
        
        Account created = [SELECT Name, Industry FROM Account WHERE Id = :accountId];
        System.assertEquals('New Corp', created.Name);
        System.assertEquals('Finance', created.Industry);
    }
    
    @isTest
    static void testDeleteAccount() {
        Account acc = [SELECT Id FROM Account LIMIT 1];
        
        RestRequest req = new RestRequest();
        req.requestURI = '/services/apexrest/accounts/' + acc.Id;
        req.httpMethod = 'DELETE';
        RestContext.request = req;
        
        Test.startTest();
        AccountRestService.deleteAccount();
        Test.stopTest();
        
        List<Account> remaining = [SELECT Id FROM Account WHERE Id = :acc.Id];
        System.assertEquals(0, remaining.size());
    }
}
```

---

## Calling from Python

```python
from sf_auth import SalesforceAuth
import requests

auth = SalesforceAuth(
    username="priyanka.joshi547@agentforce.com",
    password="Priyanka21#",
    security_token="vHnao3amdKeuFFObAVVuqmluH",
)
auth.authenticate_simple()

base_url = f"{auth.instance_url}/services/apexrest"
headers = auth.get_headers()

# Create
response = requests.post(f"{base_url}/accounts/", headers=headers, json={
    "name": "API Created Corp",
    "industry": "Technology",
    "phone": "555-9999"
})
account_id = response.json()
print(f"Created: {account_id}")

# Read
response = requests.get(f"{base_url}/accounts/{account_id}", headers=headers)
print(response.json())

# Update
response = requests.patch(f"{base_url}/accounts/{account_id}", headers=headers, json={
    "industry": "Finance"
})

# Delete
response = requests.delete(f"{base_url}/accounts/{account_id}", headers=headers)
```

---

## Calling from cURL

```bash
# Create
curl -X POST https://yourorg.my.salesforce.com/services/apexrest/accounts/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme","industry":"Tech","phone":"555-1234"}'

# Read
curl https://yourorg.my.salesforce.com/services/apexrest/accounts/001xxx \
  -H "Authorization: Bearer <token>"
```
