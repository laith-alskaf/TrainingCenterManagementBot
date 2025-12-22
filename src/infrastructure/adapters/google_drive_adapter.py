"""
Google Drive adapter for file uploads and management.
"""
import logging
import os
from typing import List, Optional
import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import io

logger = logging.getLogger(__name__)


class GoogleDriveAdapter:
    """Adapter for Google Drive API operations."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, service_account_file: str, folder_id: str):
        """
        Initialize the Google Drive adapter.
        
        Args:
            service_account_file: Path to service account JSON file
            folder_id: Default folder ID for uploads
        """
        self._service_account_file = service_account_file
        self._folder_id = folder_id
        self._service = None
    
    def _get_service(self):
        """Get or create the Drive service."""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self._service_account_file,
                scopes=self.SCOPES
            )
            self._service = build('drive', 'v3', credentials=credentials)
        return self._service
    
    async def upload_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> str:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Local path to the file
            file_name: Name for the file in Drive (defaults to original name)
            folder_id: Folder to upload to (defaults to configured folder)
            
        Returns:
            Shareable link to the uploaded file
        """
        try:
            service = self._get_service()
            folder = folder_id or self._folder_id
            name = file_name or os.path.basename(file_path)
            
            file_metadata = {
                'name': name,
                'parents': [folder]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            # Make the file publicly accessible
            await self._make_public(file['id'])
            
            logger.info(f"Uploaded file {name} to Google Drive: {file['id']}")
            return file.get('webViewLink', f"https://drive.google.com/file/d/{file['id']}/view")
            
        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {e}")
            raise
    
    async def upload_file_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> str:
        """
        Upload file bytes to Google Drive.
        
        Args:
            file_bytes: File content as bytes
            file_name: Name for the file
            mime_type: MIME type of the file
            folder_id: Folder to upload to
            
        Returns:
            Shareable link to the uploaded file
        """
        try:
            service = self._get_service()
            folder = folder_id or self._folder_id
            
            file_metadata = {
                'name': file_name,
                'parents': [folder]
            }
            
            media = MediaIoBaseUpload(
                io.BytesIO(file_bytes),
                mimetype=mime_type,
                resumable=True
            )
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            await self._make_public(file['id'])
            
            logger.info(f"Uploaded file {file_name} to Google Drive: {file['id']}")
            return file.get('webViewLink', f"https://drive.google.com/file/d/{file['id']}/view")
            
        except Exception as e:
            logger.error(f"Failed to upload file bytes to Google Drive: {e}")
            raise
    
    async def _make_public(self, file_id: str) -> None:
        """Make a file publicly accessible."""
        try:
            service = self._get_service()
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to make file public: {e}")
    
    async def list_files(self, folder_id: Optional[str] = None) -> List[dict]:
        """
        List files in a folder.
        
        Args:
            folder_id: Folder to list (defaults to configured folder)
            
        Returns:
            List of file metadata dicts
        """
        try:
            service = self._get_service()
            folder = folder_id or self._folder_id
            
            results = service.files().list(
                q=f"'{folder}' in parents and trashed=false",
                fields="files(id, name, webViewLink, mimeType, size)"
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise
    
    async def get_shareable_link(self, file_id: str) -> str:
        """Get shareable link for a file."""
        try:
            service = self._get_service()
            file = service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            return file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
        except Exception as e:
            logger.error(f"Failed to get shareable link: {e}")
            raise
    
    async def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID
            
        Returns:
            Created folder ID
        """
        try:
            service = self._get_service()
            
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            elif self._folder_id:
                file_metadata['parents'] = [self._folder_id]
            
            folder = service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            logger.info(f"Created folder {name}: {folder['id']}")
            return folder['id']
            
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            raise
