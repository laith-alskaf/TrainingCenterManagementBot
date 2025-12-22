"""
Google Sheets adapter for reading scheduled posts.
Columns: content | image_url | date | time | platform | status
"""
import logging
from typing import List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

from  domain.entities import ScheduledPost, Platform, PostStatus
from  domain.value_objects import parse_datetime_syria

logger = logging.getLogger(__name__)


class GoogleSheetsAdapter:
    """Adapter for Google Sheets API operations."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    # Column indices (0-based)
    COL_CONTENT = 0
    COL_IMAGE_URL = 1
    COL_DATE = 2
    COL_TIME = 3
    COL_PLATFORM = 4
    COL_STATUS = 5
    
    def __init__(self, service_account_file: str, spreadsheet_id: str, sheet_name: str = "Sheet1"):
        """
        Initialize the Google Sheets adapter.
        
        Args:
            service_account_file: Path to service account JSON file
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the sheet tab (e.g., "Sheet1" or "Posts")
        """
        self._service_account_file = service_account_file
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._service = None
    
    def _get_service(self):
        """Get or create the Sheets service."""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self._service_account_file,
                scopes=self.SCOPES
            )
            self._service = build('sheets', 'v4', credentials=credentials)
        return self._service
    
    def _parse_platform(self, value: str) -> Platform:
        """Parse platform value from sheet."""
        value = value.strip().lower()
        if value == "facebook":
            return Platform.FACEBOOK
        elif value == "instagram":
            return Platform.INSTAGRAM
        elif value == "both":
            return Platform.BOTH
        else:
            logger.warning(f"Unknown platform: {value}, defaulting to BOTH")
            return Platform.BOTH
    
    async def get_scheduled_posts(self, sheet_name: str = None) -> List[ScheduledPost]:
        """
        Read scheduled posts from Google Sheets.
        Only returns rows with status = 'pending'.
        
        Args:
            sheet_name: Name of the sheet to read (defaults to configured name)
            
        Returns:
            List of ScheduledPost entities
        """
        if sheet_name is None:
            sheet_name = self._sheet_name
        try:
            service = self._get_service()
            
            # Read all data from the sheet (skip header row)
            result = service.spreadsheets().values().get(
                spreadsheetId=self._spreadsheet_id,
                range=f"{sheet_name}!A2:F"
            ).execute()
            
            rows = result.get('values', [])
            posts = []
            
            for row_idx, row in enumerate(rows, start=2):  # Start at 2 (1-indexed, after header)
                try:
                    # Skip if not enough columns
                    if len(row) < 6:
                        logger.warning(f"Row {row_idx} has insufficient columns, skipping")
                        continue
                    
                    content = row[self.COL_CONTENT].strip()
                    image_url = row[self.COL_IMAGE_URL].strip() if row[self.COL_IMAGE_URL] else None
                    date_str = row[self.COL_DATE].strip()
                    time_str = row[self.COL_TIME].strip()
                    platform_str = row[self.COL_PLATFORM].strip()
                    status_str = row[self.COL_STATUS].strip().lower()
                    
                    # Only process pending posts
                    if status_str != "pending":
                        continue
                    
                    # Parse datetime (Syria timezone)
                    scheduled_dt = parse_datetime_syria(date_str, time_str)
                    platform = self._parse_platform(platform_str)
                    
                    post = ScheduledPost.create(
                        content=content,
                        scheduled_datetime=scheduled_dt,
                        platform=platform,
                        image_url=image_url if image_url else None,
                        sheet_row_index=row_idx,
                    )
                    
                    posts.append(post)
                    
                except Exception as e:
                    logger.error(f"Error parsing row {row_idx}: {e}")
                    continue
            
            logger.info(f"Found {len(posts)} pending posts in Google Sheets")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to read scheduled posts from Google Sheets: {e}")
            raise
    
    async def mark_post_published(
        self,
        row_index: int,
        sheet_name: str = None
    ) -> None:
        """
        Mark a post as published in Google Sheets.
        Updates the status column to 'published'.
        
        Args:
            row_index: Row index (1-indexed)
            sheet_name: Name of the sheet (defaults to configured name)
        """
        if sheet_name is None:
            sheet_name = self._sheet_name
        try:
            service = self._get_service()
            
            # Update status column (F = 6th column)
            range_name = f"{sheet_name}!F{row_index}"
            
            service.spreadsheets().values().update(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [['published']]}
            ).execute()
            
            logger.info(f"Marked row {row_index} as published in Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to mark post as published: {e}")
            raise
    
    async def add_error_note(
        self,
        row_index: int,
        error_message: str,
        sheet_name: str = None
    ) -> None:
        """
        Add an error note to a row (in column G).
        
        Args:
            row_index: Row index (1-indexed)
            error_message: Error message to add
            sheet_name: Name of the sheet (defaults to configured name)
        """
        if sheet_name is None:
            sheet_name = self._sheet_name
        try:
            service = self._get_service()
            
            range_name = f"{sheet_name}!G{row_index}"
            
            service.spreadsheets().values().update(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [[error_message]]}
            ).execute()
            
            logger.info(f"Added error note to row {row_index}")
            
        except Exception as e:
            logger.error(f"Failed to add error note: {e}")
