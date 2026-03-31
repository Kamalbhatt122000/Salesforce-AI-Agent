"""
Salesforce Files & Attachments Client

Manage files in Salesforce using ContentVersion, ContentDocument, and ContentDocumentLink.
Supports upload, download, list, delete, and sharing operations.

Usage:
    from sf_auth import SalesforceAuth
    from sf_files_client import SalesforceFilesClient

    auth = SalesforceAuth(username=..., password=..., security_token=...)
    auth.authenticate_simple()

    files_client = SalesforceFilesClient(auth)
    
    # Upload a file
    content_doc_id = files_client.upload_file(
        file_path="/path/to/document.pdf",
        title="Contract",
        record_id="00Q..."
    )
    
    # List files on a record
    files = files_client.list_files(record_id="00Q...")
    
    # Download a file
    content = files_client.download_file(content_version_id="068...")
    
    # Delete a file
    files_client.delete_file(content_document_id="069...")
"""

import base64
import json
import os
import requests
from pathlib import Path


API_VERSION = "v62.0"


class SalesforceFilesClient:
    """Client for managing Salesforce files and attachments."""

    def __init__(self, auth):
        self.auth = auth
        self.base_url = f"{auth.instance_url}/services/data/{API_VERSION}"

    def _request(self, method, endpoint, data=None, params=None, headers=None):
        """Make an authenticated request to the Salesforce REST API."""
        url = f"{self.base_url}{endpoint}"
        
        # Merge auth headers with custom headers
        request_headers = self.auth.get_headers()
        if headers:
            request_headers.update(headers)

        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            json=data,
            params=params,
        )

        if response.status_code in (200, 201):
            # Check if response is JSON
            if response.headers.get("Content-Type", "").startswith("application/json"):
                return response.json()
            else:
                return response.content
        elif response.status_code == 204:
            return None
        else:
            error_msg = response.text
            try:
                error_msg = json.dumps(response.json(), indent=2)
            except Exception:
                pass
            raise Exception(f"API Error ({response.status_code}): {error_msg}")

    def _query(self, soql):
        """Execute a SOQL query."""
        result = self._request("GET", "/query/", params={"q": soql})
        return result.get("records", [])

    # ── Upload File ───────────────────────────────────────────

    def upload_file(self, file_path=None, file_content=None, title=None, 
                    record_id=None, description=None):
        """
        Upload a file to Salesforce and optionally link it to a record.
        
        Args:
            file_path: Path to the file to upload (if uploading from disk)
            file_content: Base64-encoded file content (if already encoded)
            title: Display name for the file (defaults to filename)
            record_id: Record ID to attach the file to (optional)
            description: File description (optional)
        
        Returns:
            Dictionary with ContentDocumentId and ContentVersionId
        """
        # Read file content
        if file_path:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            
            file_content_b64 = base64.b64encode(file_bytes).decode("utf-8")
            
            if not title:
                title = file_path.name
            
            path_on_client = file_path.name
        
        elif file_content:
            # Assume file_content is already base64-encoded
            file_content_b64 = file_content
            path_on_client = title or "file"
        
        else:
            raise ValueError("Either file_path or file_content must be provided")

        # Create ContentVersion (this creates the file)
        content_version_data = {
            "Title": title,
            "PathOnClient": path_on_client,
            "VersionData": file_content_b64,
        }
        
        if description:
            content_version_data["Description"] = description

        result = self._request(
            "POST",
            "/sobjects/ContentVersion/",
            data=content_version_data
        )

        if not result.get("success"):
            raise Exception(f"Failed to upload file: {result}")

        content_version_id = result["id"]
        print(f"✅ Uploaded file: {title} (ContentVersion: {content_version_id})")

        # Get the ContentDocumentId
        query = f"""
            SELECT ContentDocumentId 
            FROM ContentVersion 
            WHERE Id = '{content_version_id}'
        """
        cv_records = self._query(query)
        
        if not cv_records:
            raise Exception("Failed to retrieve ContentDocumentId after upload")
        
        content_document_id = cv_records[0]["ContentDocumentId"]

        # Link to record if provided
        if record_id:
            self.share_file_with_record(
                content_document_id=content_document_id,
                record_id=record_id,
                share_type="V"
            )
            print(f"✅ Linked file to record: {record_id}")

        return {
            "ContentDocumentId": content_document_id,
            "ContentVersionId": content_version_id,
            "Title": title
        }

    # ── List Files ────────────────────────────────────────────

    def list_files(self, record_id):
        """
        List all files attached to a specific record.
        
        Args:
            record_id: The record ID to query files for
        
        Returns:
            List of file dictionaries with metadata
        """
        query = f"""
            SELECT ContentDocument.Id,
                   ContentDocument.Title,
                   ContentDocument.FileType,
                   ContentDocument.FileExtension,
                   ContentDocument.ContentSize,
                   ContentDocument.CreatedDate,
                   ContentDocument.CreatedBy.Name,
                   ContentDocument.LatestPublishedVersionId
            FROM ContentDocumentLink
            WHERE LinkedEntityId = '{record_id}'
            ORDER BY ContentDocument.CreatedDate DESC
        """

        records = self._query(query)

        files = []
        for record in records:
            cd = record.get("ContentDocument", {})
            files.append({
                "ContentDocumentId": cd.get("Id"),
                "ContentVersionId": cd.get("LatestPublishedVersionId"),
                "Title": cd.get("Title"),
                "FileType": cd.get("FileType"),
                "FileExtension": cd.get("FileExtension"),
                "ContentSize": cd.get("ContentSize"),
                "CreatedDate": cd.get("CreatedDate"),
                "CreatedBy": cd.get("CreatedBy", {}).get("Name"),
            })

        print(f"📎 Found {len(files)} file(s) on record {record_id}")
        return files

    # ── Download File ─────────────────────────────────────────

    def download_file(self, content_version_id):
        """
        Download a file by ContentVersion ID.
        
        Args:
            content_version_id: The ContentVersion ID
        
        Returns:
            Dictionary with file content (bytes) and metadata
        """
        # Get file metadata
        query = f"""
            SELECT Title, FileType, FileExtension, ContentSize, VersionData
            FROM ContentVersion
            WHERE Id = '{content_version_id}'
        """
        records = self._query(query)

        if not records:
            raise Exception(f"ContentVersion not found: {content_version_id}")

        metadata = records[0]

        # Download the binary content
        endpoint = f"/sobjects/ContentVersion/{content_version_id}/VersionData"
        file_content = self._request("GET", endpoint)

        print(f"📥 Downloaded: {metadata['Title']} ({metadata.get('ContentSize', 0)} bytes)")

        return {
            "content": file_content,
            "title": metadata["Title"],
            "file_type": metadata.get("FileType"),
            "file_extension": metadata.get("FileExtension"),
            "size": metadata.get("ContentSize"),
        }

    def download_file_to_disk(self, content_version_id, output_path=None):
        """
        Download a file and save it to disk.
        
        Args:
            content_version_id: The ContentVersion ID
            output_path: Path to save the file (defaults to current directory)
        
        Returns:
            Path to the saved file
        """
        file_data = self.download_file(content_version_id)

        if not output_path:
            # Use the file's title and extension
            filename = file_data["title"]
            if file_data.get("file_extension"):
                filename = f"{filename}.{file_data['file_extension']}"
            output_path = Path.cwd() / filename
        else:
            output_path = Path(output_path)

        # Write to disk
        with open(output_path, "wb") as f:
            f.write(file_data["content"])

        print(f"💾 Saved to: {output_path}")
        return str(output_path)

    # ── Delete File ───────────────────────────────────────────

    def delete_file(self, content_document_id):
        """
        Delete a file (ContentDocument) from Salesforce.
        This deletes all versions and all links to records.
        
        Args:
            content_document_id: The ContentDocument ID to delete
        """
        self._request("DELETE", f"/sobjects/ContentDocument/{content_document_id}")
        print(f"🗑️  Deleted ContentDocument: {content_document_id}")

    # ── Share File ────────────────────────────────────────────

    def share_file_with_record(self, content_document_id, record_id, share_type="V"):
        """
        Link an existing file to a record (create ContentDocumentLink).
        
        Args:
            content_document_id: The ContentDocument ID to share
            record_id: The record ID to link the file to
            share_type: V (Viewer), C (Collaborator), I (Inferred)
        
        Returns:
            ContentDocumentLink ID
        """
        link_data = {
            "ContentDocumentId": content_document_id,
            "LinkedEntityId": record_id,
            "ShareType": share_type,
        }

        result = self._request("POST", "/sobjects/ContentDocumentLink/", data=link_data)

        if not result.get("success"):
            raise Exception(f"Failed to share file: {result}")

        print(f"🔗 Shared file {content_document_id} with record {record_id}")
        return result["id"]

    # ── Get File Details ──────────────────────────────────────

    def get_file_details(self, content_document_id):
        """
        Get detailed metadata for a file.
        
        Args:
            content_document_id: The ContentDocument ID
        
        Returns:
            Dictionary with file metadata
        """
        query = f"""
            SELECT Id, Title, FileType, FileExtension, ContentSize,
                   CreatedDate, CreatedById, CreatedBy.Name,
                   LastModifiedDate, LastModifiedById, LastModifiedBy.Name,
                   OwnerId, Owner.Name,
                   LatestPublishedVersionId
            FROM ContentDocument
            WHERE Id = '{content_document_id}'
        """

        records = self._query(query)

        if not records:
            raise Exception(f"ContentDocument not found: {content_document_id}")

        doc = records[0]
        
        return {
            "Id": doc.get("Id"),
            "Title": doc.get("Title"),
            "FileType": doc.get("FileType"),
            "FileExtension": doc.get("FileExtension"),
            "ContentSize": doc.get("ContentSize"),
            "CreatedDate": doc.get("CreatedDate"),
            "CreatedBy": doc.get("CreatedBy", {}).get("Name"),
            "LastModifiedDate": doc.get("LastModifiedDate"),
            "LastModifiedBy": doc.get("LastModifiedBy", {}).get("Name"),
            "Owner": doc.get("Owner", {}).get("Name"),
            "LatestPublishedVersionId": doc.get("LatestPublishedVersionId"),
        }

    # ── Utility Methods ───────────────────────────────────────

    def format_file_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes is None:
            return "Unknown"
        
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def list_all_files_in_org(self, limit=100):
        """
        List recent files in the org (not filtered by record).
        
        Args:
            limit: Maximum number of files to return
        
        Returns:
            List of file dictionaries
        """
        query = f"""
            SELECT Id, Title, FileType, FileExtension, ContentSize,
                   CreatedDate, CreatedBy.Name
            FROM ContentDocument
            ORDER BY CreatedDate DESC
            LIMIT {limit}
        """

        records = self._query(query)

        files = []
        for record in records:
            files.append({
                "ContentDocumentId": record.get("Id"),
                "Title": record.get("Title"),
                "FileType": record.get("FileType"),
                "FileExtension": record.get("FileExtension"),
                "ContentSize": record.get("ContentSize"),
                "CreatedDate": record.get("CreatedDate"),
                "CreatedBy": record.get("CreatedBy", {}).get("Name"),
            })

        print(f"📎 Found {len(files)} recent file(s) in org")
        return files


if __name__ == "__main__":
    # Example usage
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent / "salesforce" / "scripts"))
    
    from sf_auth import SalesforceAuth

    auth = SalesforceAuth()
    auth.authenticate_simple()

    files_client = SalesforceFilesClient(auth)

    # List recent files
    print("\n=== Recent Files in Org ===")
    files = files_client.list_all_files_in_org(limit=5)
    for f in files:
        size = files_client.format_file_size(f.get("ContentSize"))
        print(f"  {f['Title']} ({f.get('FileType', 'N/A')}) - {size}")
