"""
Example: Using the Salesforce Files Skill

This script demonstrates common file operations in Salesforce:
- Upload a file to a Lead
- List all files on the Lead
- Download a file
- Share a file with multiple records
- Delete a file
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent / "salesforce" / "scripts"))
sys.path.append(str(Path(__file__).parent.parent / ".agents" / "skills" / "salesforce-files" / "scripts"))

from sf_auth import SalesforceAuth
from sf_files_client import SalesforceFilesClient
from sf_rest_client import SalesforceRESTClient


def main():
    print("=" * 60)
    print("Salesforce Files Skill - Example Usage")
    print("=" * 60)
    
    # 1. Authenticate
    print("\n[1] Authenticating to Salesforce...")
    auth = SalesforceAuth()
    auth.authenticate_simple()
    print(f"✅ Connected to: {auth.instance_url}")
    
    # Initialize clients
    files_client = SalesforceFilesClient(auth)
    rest_client = SalesforceRESTClient(auth)
    
    # 2. Create a test Lead (for demonstration)
    print("\n[2] Creating a test Lead...")
    lead_data = {
        "FirstName": "John",
        "LastName": "Doe",
        "Company": "Test Company",
        "Email": "john.doe@example.com",
        "Status": "Open - Not Contacted"
    }
    lead_id = rest_client.create("Lead", lead_data)
    print(f"✅ Created Lead: {lead_id}")
    
    # 3. Create a sample file to upload
    print("\n[3] Creating a sample file...")
    sample_file = Path("sample_document.txt")
    with open(sample_file, "w") as f:
        f.write("This is a sample document for Salesforce file upload demo.\n")
        f.write("Created by the salesforce-files skill.\n")
        f.write("\nTimestamp: 2024-01-15 10:30:00\n")
    print(f"✅ Created: {sample_file}")
    
    # 4. Upload file to Lead
    print("\n[4] Uploading file to Lead...")
    upload_result = files_client.upload_file(
        file_path=str(sample_file),
        title="Sample Document",
        record_id=lead_id,
        description="Demo file for testing"
    )
    content_doc_id = upload_result['ContentDocumentId']
    content_version_id = upload_result['ContentVersionId']
    print(f"✅ Uploaded: {upload_result['Title']}")
    print(f"   ContentDocument ID: {content_doc_id}")
    print(f"   ContentVersion ID: {content_version_id}")
    
    # 5. List files on the Lead
    print("\n[5] Listing files on Lead...")
    files = files_client.list_files(record_id=lead_id)
    print(f"✅ Found {len(files)} file(s):")
    for file in files:
        size = files_client.format_file_size(file['ContentSize'])
        print(f"   - {file['Title']} ({file['FileType']}) - {size}")
        print(f"     Created: {file['CreatedDate']} by {file['CreatedBy']}")
    
    # 6. Get file details
    print("\n[6] Getting file details...")
    details = files_client.get_file_details(content_doc_id)
    print(f"✅ File Details:")
    print(f"   Title: {details['Title']}")
    print(f"   Type: {details['FileType']}")
    print(f"   Size: {files_client.format_file_size(details['ContentSize'])}")
    print(f"   Owner: {details['Owner']}")
    print(f"   Created: {details['CreatedDate']}")
    
    # 7. Download the file
    print("\n[7] Downloading file...")
    download_path = files_client.download_file_to_disk(
        content_version_id=content_version_id,
        output_path="downloaded_sample.txt"
    )
    print(f"✅ Downloaded to: {download_path}")
    
    # 8. Create another Lead and share the file
    print("\n[8] Creating second Lead and sharing file...")
    lead2_data = {
        "FirstName": "Jane",
        "LastName": "Smith",
        "Company": "Another Company",
        "Email": "jane.smith@example.com",
        "Status": "Open - Not Contacted"
    }
    lead2_id = rest_client.create("Lead", lead2_data)
    print(f"✅ Created second Lead: {lead2_id}")
    
    # Share the file with the second Lead
    files_client.share_file_with_record(
        content_document_id=content_doc_id,
        record_id=lead2_id,
        share_type="V"  # Viewer access
    )
    print(f"✅ Shared file with second Lead")
    
    # Verify the file is now on both Leads
    print("\n[9] Verifying file is shared...")
    query = f"""
        SELECT LinkedEntityId, LinkedEntity.Name, ShareType
        FROM ContentDocumentLink
        WHERE ContentDocumentId = '{content_doc_id}'
    """
    links = rest_client.query(query)
    print(f"✅ File is linked to {len(links)} record(s):")
    for link in links:
        entity_name = link.get('LinkedEntity', {}).get('Name', 'Unknown')
        print(f"   - {entity_name} (ShareType: {link['ShareType']})")
    
    # 10. Cleanup (optional - uncomment to delete test data)
    print("\n[10] Cleanup...")
    cleanup = input("Delete test data? (y/n): ").lower()
    
    if cleanup == 'y':
        # Delete file
        files_client.delete_file(content_doc_id)
        print(f"✅ Deleted file: {content_doc_id}")
        
        # Delete Leads
        rest_client.delete("Lead", lead_id)
        rest_client.delete("Lead", lead2_id)
        print(f"✅ Deleted Leads: {lead_id}, {lead2_id}")
        
        # Delete local files
        sample_file.unlink()
        Path(download_path).unlink()
        print(f"✅ Deleted local files")
    else:
        print("⚠️  Test data not deleted. Clean up manually if needed.")
        print(f"   Lead 1: {lead_id}")
        print(f"   Lead 2: {lead2_id}")
        print(f"   File: {content_doc_id}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
