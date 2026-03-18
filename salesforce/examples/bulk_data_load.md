# Example: Bulk Data Load

Loading 100,000+ records into Salesforce using Bulk API 2.0.

---

## Using Python Scripts

```python
from sf_auth import SalesforceAuth
from sf_bulk_client import SalesforceBulkClient

# Authenticate
auth = SalesforceAuth(
    username="priyanka.joshi547@agentforce.com",
    password="Priyanka21#",
    security_token="vHnao3amdKeuFFObAVVuqmluH",
)
auth.authenticate_simple()

bulk = SalesforceBulkClient(auth)

# ── Method 1: Inline CSV ───────────────────────────
csv_data = """Name,Industry,Phone,Website
Acme Corp,Technology,555-0001,https://acme.example.com
Beta Inc,Finance,555-0002,https://beta.example.com
Gamma LLC,Healthcare,555-0003,https://gamma.example.com"""

job_id = bulk.insert_csv("Account", csv_data)
bulk.wait_for_completion(job_id)
results = bulk.get_results(job_id)

print("Successful:", results["successful"][:200])
print("Failed:", results["failed"][:200])

# ── Method 2: From a CSV File ──────────────────────
with open("accounts.csv", "r") as f:
    csv_from_file = f.read()

job_id = bulk.insert_csv("Account", csv_from_file)
bulk.wait_for_completion(job_id)

# ── Method 3: Generate Large Dataset ───────────────
import csv
import io

# Generate 100k records
output = io.StringIO()
writer = csv.writer(output)
writer.writerow(["Name", "Industry", "Phone"])

for i in range(100000):
    writer.writerow([f"Company_{i:06d}", "Technology", f"555-{i:04d}"])

csv_data = output.getvalue()

# Split into chunks < 150 MB if needed
chunk_size = 100 * 1024 * 1024  # 100 MB
if len(csv_data) > chunk_size:
    lines = csv_data.split("\n")
    header = lines[0]
    chunks = []
    current_chunk = [header]
    current_size = len(header)

    for line in lines[1:]:
        if current_size + len(line) > chunk_size:
            chunks.append("\n".join(current_chunk))
            current_chunk = [header]
            current_size = len(header)
        current_chunk.append(line)
        current_size += len(line)

    if len(current_chunk) > 1:
        chunks.append("\n".join(current_chunk))

    # Upload each chunk
    for i, chunk in enumerate(chunks):
        print(f"Uploading chunk {i+1}/{len(chunks)}...")
        job_id = bulk.insert_csv("Account", chunk)
        bulk.wait_for_completion(job_id)
else:
    job_id = bulk.insert_csv("Account", csv_data)
    bulk.wait_for_completion(job_id)
```

---

## Bulk Update

```python
# CSV must include the 'Id' column
update_csv = """Id,Industry
001xxx000000001,Finance
001xxx000000002,Healthcare
001xxx000000003,Technology"""

job_id = bulk.update_csv("Account", update_csv)
bulk.wait_for_completion(job_id)
```

## Bulk Delete

```python
# CSV with only the 'Id' column
delete_csv = """Id
001xxx000000001
001xxx000000002
001xxx000000003"""

job_id = bulk.delete_csv("Account", delete_csv)
bulk.wait_for_completion(job_id)
```

## Bulk Upsert (by External ID)

```python
upsert_csv = """External_Id__c,Name,Industry
EXT-001,Acme Corp,Technology
EXT-002,Beta Inc,Finance"""

job_id = bulk.create_job("Account", "upsert", external_id_field="External_Id__c")
bulk.upload_csv(job_id, upsert_csv)
bulk.close_job(job_id)
bulk.wait_for_completion(job_id)
```

## Bulk Query (Extract Data)

```python
job_id = bulk.create_query_job("SELECT Id, Name, Industry FROM Account")
status = bulk.wait_for_completion(job_id)

if status.get("state") == "JobComplete":
    csv_results = bulk.get_query_results(job_id)
    
    # Save to file
    with open("account_export.csv", "w") as f:
        f.write(csv_results)
    
    print(f"Exported to account_export.csv")
```

---

## Error Handling

Always check failed results:

```python
results = bulk.get_results(job_id)

if results["failed"].strip():
    print("⚠️ Some records failed:")
    print(results["failed"])
    
    # Parse failed CSV
    import csv
    reader = csv.DictReader(io.StringIO(results["failed"]))
    for row in reader:
        print(f"  Error: {row.get('sf__Error', 'Unknown')}")
```
