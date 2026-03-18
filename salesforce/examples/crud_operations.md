# Example: CRUD Operations

Step-by-step examples for Create, Read, Update, Delete operations using the REST API and Python scripts.

---

## Using Python Scripts

```python
from sf_auth import SalesforceAuth
from sf_rest_client import SalesforceRESTClient

# 1. Authenticate
auth = SalesforceAuth(
    username="priyanka.joshi547@agentforce.com",
    password="Priyanka21#",
    security_token="vHnao3amdKeuFFObAVVuqmluH",
)
auth.authenticate_simple()

client = SalesforceRESTClient(auth)

# 2. CREATE — Create a new Account
account_id = client.create("Account", {
    "Name": "Acme Corporation",
    "Industry": "Technology",
    "Phone": "555-1234",
    "Website": "https://acme.example.com",
    "Description": "A leading technology company",
})
print(f"Created Account: {account_id}")

# 3. READ — Read the Account back
account = client.read("Account", account_id)
print(f"Account Name: {account['Name']}")
print(f"Industry: {account['Industry']}")

# Read specific fields only
account_partial = client.read("Account", account_id, fields=["Name", "Phone"])
print(f"Phone: {account_partial['Phone']}")

# 4. UPDATE — Update the phone number
client.update("Account", account_id, {
    "Phone": "555-5678",
    "Description": "Updated description",
})

# Verify the update
updated = client.read("Account", account_id, fields=["Phone", "Description"])
print(f"Updated Phone: {updated['Phone']}")

# 5. DELETE — Delete the Account
client.delete("Account", account_id)
print("Account deleted successfully")
```

---

## Using REST API Directly (cURL)

### Create
```bash
curl -X POST https://yourorg.my.salesforce.com/services/data/v62.0/sobjects/Account/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"Name": "Acme Corp", "Industry": "Technology"}'
```

### Read
```bash
curl https://yourorg.my.salesforce.com/services/data/v62.0/sobjects/Account/001xxx \
  -H "Authorization: Bearer <token>"
```

### Update
```bash
curl -X PATCH https://yourorg.my.salesforce.com/services/data/v62.0/sobjects/Account/001xxx \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"Phone": "555-5678"}'
```

### Delete
```bash
curl -X DELETE https://yourorg.my.salesforce.com/services/data/v62.0/sobjects/Account/001xxx \
  -H "Authorization: Bearer <token>"
```

---

## Creating Related Records

```python
# Create an Account and a Contact for it
account_id = client.create("Account", {"Name": "Beta Inc"})

contact_id = client.create("Contact", {
    "FirstName": "John",
    "LastName": "Smith",
    "Email": "john.smith@beta.example.com",
    "AccountId": account_id,  # Link to the Account
})

print(f"Created Contact {contact_id} linked to Account {account_id}")
```

## Composite Create (Parent + Children in One Call)

```python
composite_data = client.composite([
    {
        "method": "POST",
        "url": "/services/data/v62.0/sobjects/Account/",
        "referenceId": "newAccount",
        "body": {"Name": "Gamma Corp"}
    },
    {
        "method": "POST",
        "url": "/services/data/v62.0/sobjects/Contact/",
        "referenceId": "newContact",
        "body": {
            "LastName": "Jones",
            "AccountId": "@{newAccount.id}"
        }
    }
])
print(composite_data)
```
