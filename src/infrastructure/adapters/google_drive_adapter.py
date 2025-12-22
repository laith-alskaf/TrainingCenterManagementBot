"""
Google Drive adapter for file uploads and management.
Uses OAuth for all operations to save files in user's personal Drive.
"""
import json
import logging
import os
from typing import List, Optional
from pathlib import Path
import io

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

logger = logging.getLogger(__name__)


class GoogleDriveAdapter:
    """
    Adapter for Google Drive API operations.
    
    Uses OAuth for all operations to save files in user's personal Drive,
    avoiding Service Account storage quota issues.
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    TOKEN_FILE = 'token.json'  # Stores OAuth tokens
    
    def __init__(
        self,
        service_account_file: str,  # Kept for backward compatibility
        folder_id: str,
        oauth_client_secret_file: str = "client_secret.json",
    ):
        """
        Initialize the Google Drive adapter.
        
        Args:
            service_account_file: (Deprecated) Path to service account file
            folder_id: Default folder ID for uploads
            oauth_client_secret_file: Path to OAuth client secret file
        """
        self._folder_id = folder_id
        self._oauth_client_secret_file = oauth_client_secret_file
        self._oauth_service = None
    
    def _get_oauth_credentials(self):
        """Get OAuth credentials for user authentication."""
        creds = None
        
        # Check if token is provided via environment variable (for server deployment)
        # This allows running on servers without browser access
        token_env = os.getenv('GOOGLE_OAUTH_TOKEN', '')
        if token_env.strip().startswith('{') and not os.path.exists(self.TOKEN_FILE):
            try:
                import json
                # Validate JSON and write to token file
                token_data = json.loads(token_env)
                with open(self.TOKEN_FILE, 'w') as f:
                    json.dump(token_data, f)
                logger.info(f"Created {self.TOKEN_FILE} from GOOGLE_OAUTH_TOKEN environment variable")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GOOGLE_OAUTH_TOKEN: {e}")
            except Exception as e:
                logger.error(f"Failed to create token file from env: {e}")
        
        # Check if we have saved token
        if os.path.exists(self.TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load token file: {e}")
                creds = None
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                # Check if it's JSON content (starts with {)
                if self._oauth_client_secret_file.strip().startswith('{'):
                    # Parse JSON content directly
                    try:
                        import json
                        import tempfile
                        client_config = json.loads(self._oauth_client_secret_file)
                        
                        # Create a temporary file for InstalledAppFlow
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                            json.dump(client_config, temp_file)
                            temp_path = temp_file.name
                        
                        flow = InstalledAppFlow.from_client_secrets_file(
                            temp_path,
                            self.SCOPES
                        )
                        
                        # Clean up temp file
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse OAuth client secret JSON: {e}")
                        raise
                else:
                    # It's a file path
                    if not os.path.exists(self._oauth_client_secret_file):
                        raise FileNotFoundError(
                            f"OAuth client secret file not found: {self._oauth_client_secret_file}. "
                            f"Please download it from Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self._oauth_client_secret_file,
                        self.SCOPES
                    )
                
                creds = flow.run_local_server(port=0)
                
                # Save token for next time
                with open(self.TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"OAuth token saved to {self.TOKEN_FILE}")
        
        return creds
    
    def _get_service(self):
        """Get Drive service using OAuth."""
        if self._oauth_service is None:
            credentials = self._get_oauth_credentials()
            self._oauth_service = build('drive', 'v3', credentials=credentials)
        return self._oauth_service
    
    async def upload_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> str:
        """
        Upload a file to Google Drive using OAuth.
        
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
        Upload file bytes to Google Drive using OAuth.
        
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
        Create a folder in Google Drive using OAuth.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (defaults to configured folder)
            
        Returns:
            Created folder ID
        """
        try:
            service = self._get_service()
            parent = parent_id or self._folder_id
            
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent] if parent else []
            }
            
            folder = service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder['id']
            logger.info(f"Created folder {name}: {folder_id}")
            return folder_id
            
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            raise
