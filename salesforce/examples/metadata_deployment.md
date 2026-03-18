# Example: Metadata Deployment

Deploying metadata between Salesforce orgs (sandbox → production).

---

## Using Salesforce CLI (sf/sfdx)

### Setup
```bash
# Install Salesforce CLI
npm install -g @salesforce/cli

# Authenticate to source org
sf org login web --alias my-sandbox --instance-url https://test.salesforce.com

# Authenticate to target org
sf org login web --alias my-production --instance-url https://login.salesforce.com
```

### Retrieve Metadata
```bash
# Retrieve specific components
sf project retrieve start \
  --metadata ApexClass:AccountService \
  --metadata ApexClass:AccountServiceTest \
  --metadata CustomObject:Invoice__c \
  --target-org my-sandbox

# Retrieve using package.xml
sf project retrieve start \
  --manifest manifest/package.xml \
  --target-org my-sandbox
```

### Deploy Metadata
```bash
# Deploy to production (with tests)
sf project deploy start \
  --manifest manifest/package.xml \
  --target-org my-production \
  --test-level RunLocalTests

# Validate only (dry run)
sf project deploy start \
  --manifest manifest/package.xml \
  --target-org my-production \
  --test-level RunLocalTests \
  --dry-run

# Deploy specific components
sf project deploy start \
  --metadata ApexClass:AccountService \
  --target-org my-production
```

---

## Package.xml Examples

### Deploy Apex Classes
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>AccountService</members>
    <members>AccountServiceTest</members>
    <name>ApexClass</name>
  </types>
  <version>62.0</version>
</Package>
```

### Deploy Custom Object with Fields
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>Invoice__c</members>
    <name>CustomObject</name>
  </types>
  <types>
    <members>Invoice__c.Amount__c</members>
    <members>Invoice__c.Status__c</members>
    <members>Invoice__c.Due_Date__c</members>
    <name>CustomField</name>
  </types>
  <version>62.0</version>
</Package>
```

### Deploy Everything
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>*</members>
    <name>ApexClass</name>
  </types>
  <types>
    <members>*</members>
    <name>ApexTrigger</name>
  </types>
  <types>
    <members>*</members>
    <name>CustomObject</name>
  </types>
  <types>
    <members>*</members>
    <name>Flow</name>
  </types>
  <types>
    <members>*</members>
    <name>Layout</name>
  </types>
  <types>
    <members>*</members>
    <name>PermissionSet</name>
  </types>
  <version>62.0</version>
</Package>
```

---

## Using REST API (Python)

```python
import requests
import base64
import zipfile
import io
from sf_auth import SalesforceAuth

auth = SalesforceAuth(
    username="priyanka.joshi547@agentforce.com",
    password="Priyanka21#",
    security_token="vHnao3amdKeuFFObAVVuqmluH",
)
auth.authenticate_simple()

# Create a ZIP with metadata
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
    # package.xml
    zf.writestr('package.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>HelloWorld</members>
    <name>ApexClass</name>
  </types>
  <version>62.0</version>
</Package>''')
    
    # Apex class
    zf.writestr('classes/HelloWorld.cls', '''public class HelloWorld {
    public static String sayHello(String name) {
        return 'Hello, ' + name + '!';
    }
}''')
    
    zf.writestr('classes/HelloWorld.cls-meta.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
  <apiVersion>62.0</apiVersion>
  <status>Active</status>
</ApexClass>''')

zip_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# Deploy via SOAP Metadata API
deploy_soap = f'''<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:met="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>{auth.access_token}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:deploy>
      <met:ZipFile>{zip_data}</met:ZipFile>
      <met:DeployOptions>
        <met:checkOnly>true</met:checkOnly>
        <met:testLevel>NoTestRun</met:testLevel>
      </met:DeployOptions>
    </met:deploy>
  </soapenv:Body>
</soapenv:Envelope>'''

response = requests.post(
    f"{auth.instance_url}/services/Soap/m/62.0",
    data=deploy_soap,
    headers={
        'Content-Type': 'text/xml; charset=UTF-8',
        'SOAPAction': 'deploy'
    }
)

print(response.text[:500])
```

---

## Best Practices

1. **Always validate first** — use `--dry-run` or `checkOnly: true`
2. **Run tests** — use `RunLocalTests` for production deployments
3. **Version control** — keep all metadata in Git
4. **Use scratch orgs** for development
5. **Destructive changes** — use `destructiveChanges.xml` for deletions
