"""
Test: Create a custom field with fullName in metadata and verify it shows up in describe.
"""
import os
import sys
import json
import requests
import time

scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salesforce", "scripts")
sys.path.insert(0, scripts_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from sf_auth import SalesforceAuth

SF_USERNAME = os.getenv("SF_USERNAME", "")
SF_PASSWORD = os.getenv("SF_PASSWORD", "")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "")

auth = SalesforceAuth(username=SF_USERNAME, password=SF_PASSWORD, security_token=SF_SECURITY_TOKEN)
auth.authenticate_simple()

headers = auth.get_headers()
base = auth.instance_url

# First, clean up the old test field
print("--- Step 1: Clean up old Test_Debug_Field ---")
tooling_url = f"{base}/services/data/v62.0/tooling/query/"
query = "SELECT Id, DeveloperName FROM CustomField WHERE TableEnumOrId = 'Lead' AND DeveloperName = 'Test_Debug_Field'"
resp = requests.get(tooling_url, headers=headers, params={"q": query})
if resp.status_code == 200:
    records = resp.json().get("records", [])
    if records:
        field_id = records[0]["Id"]
        print(f"  Found old field: {field_id}, deleting...")
        del_resp = requests.delete(f"{base}/services/data/v62.0/tooling/sobjects/CustomField/{field_id}", headers=headers)
        print(f"  Delete status: {del_resp.status_code}")
        time.sleep(3)
    else:
        print("  No old field found, good.")

# Also clean up Priority and Sales_Insight
for dev_name in ["Priority", "Sales_Insight"]:
    query = f"SELECT Id, DeveloperName FROM CustomField WHERE TableEnumOrId = 'Lead' AND DeveloperName = '{dev_name}'"
    resp = requests.get(tooling_url, headers=headers, params={"q": query})
    if resp.status_code == 200:
        records = resp.json().get("records", [])
        if records:
            field_id = records[0]["Id"]
            print(f"  Found {dev_name}: {field_id}, deleting...")
            del_resp = requests.delete(f"{base}/services/data/v62.0/tooling/sobjects/CustomField/{field_id}", headers=headers)
            print(f"  Delete status: {del_resp.status_code}")
            time.sleep(2)

print()
print("--- Step 2: Create new field with corrected payload ---")
time.sleep(3)

# Method 1: Use the Metadata API approach via composite
# The Tooling API's CustomField create should work - let's see the EXACT response
url = f"{base}/services/data/v62.0/tooling/sobjects/CustomField/"

payload = {
    "FullName": "Lead.Verify_Test__c",
    "Metadata": {
        "fullName": "Verify_Test__c",
        "label": "Verify Test",
        "type": "Text",
        "length": 255,
        "description": "Testing if field shows up",
        "inlineHelpText": "",
    }
}

print(f"Payload:\n{json.dumps(payload, indent=2)}")

response = requests.post(url, headers=headers, json=payload)
print(f"\nStatus Code: {response.status_code}")
try:
    result = response.json()
    print(f"Response:\n{json.dumps(result, indent=2)}")
except:
    print(f"Response text: {response.text}")

if response.status_code in (200, 201):
    field_id = result.get("id", "")
    print(f"\nField created with ID: {field_id}")
    
    # Wait a moment for Salesforce to process
    print("Waiting 5 seconds for Salesforce to process...")
    time.sleep(5)
    
    # Check Describe API
    print("\n--- Step 3: Check if field appears in Describe API ---")
    describe_url = f"{base}/services/data/v62.0/sobjects/Lead/describe/"
    desc_resp = requests.get(describe_url, headers=headers)
    if desc_resp.status_code == 200:
        fields = desc_resp.json().get("fields", [])
        verify_field = [f for f in fields if f["name"] == "Verify_Test__c"]
        if verify_field:
            print(f"  FOUND in Describe API: {verify_field[0]['name']} ({verify_field[0]['label']})")
        else:
            print("  NOT FOUND in Describe API!")
            custom_fields = [f["name"] for f in fields if f["custom"]]
            print(f"  All custom field names: {custom_fields}")
    
    # Clean up
    print(f"\n--- Cleanup: deleting Verify_Test field ---")
    del_resp = requests.delete(f"{base}/services/data/v62.0/tooling/sobjects/CustomField/{field_id}", headers=headers)
    print(f"  Delete status: {del_resp.status_code}")
