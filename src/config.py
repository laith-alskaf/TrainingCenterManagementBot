"""
Configuration module for the Training Center Management Platform.
Loads all settings from environment variables with validation.
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str
    admin_user_ids: List[int]
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        return user_id in self.admin_user_ids


@dataclass(frozen=True)
class MongoDBConfig:
    """MongoDB Atlas configuration."""
    uri: str
    database_name: str = "training_center"


@dataclass(frozen=True)
class GoogleConfig:
    """Google APIs configuration."""
    service_account_file: str
    drive_folder_id: str
    sheets_id: str
    sheets_name: str  # Name of the sheet tab (e.g., "Sheet1" or "Posts")
    oauth_client_secret_file: str = "client_secret.json"  # OAuth for folder creation


@dataclass(frozen=True)
class MetaConfig:
    """Meta Graph API configuration."""
    access_token: str
    facebook_page_id: str
    instagram_account_id: str


@dataclass(frozen=True)
class SchedulerConfig:
    """Scheduler configuration."""
    check_interval_minutes: int
    timezone: str


@dataclass
class Config:
    """Main application configuration."""
    telegram: TelegramConfig
    mongodb: MongoDBConfig
    google: GoogleConfig
    meta: MetaConfig
    scheduler: SchedulerConfig
    timezone: pytz.BaseTzInfo = field(init=False)
    
    def __post_init__(self):
        """Set timezone object after initialization."""
        object.__setattr__(self, 'timezone', pytz.timezone(self.scheduler.timezone))


def load_config() -> Config:
    """Load configuration from environment variables."""
    
    # Parse admin user IDs
    admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
    admin_user_ids = [
        int(uid.strip()) 
        for uid in admin_ids_str.split(",") 
        if uid.strip().isdigit()
    ]
    
    return Config(
        telegram=TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            admin_user_ids=admin_user_ids,
        ),
        mongodb=MongoDBConfig(
            uri=os.getenv("MONGODB_URI", ""),
        ),
        google=GoogleConfig(
            service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json"),
            drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""),
            sheets_id=os.getenv("GOOGLE_SHEETS_ID", ""),
            sheets_name=os.getenv("GOOGLE_SHEETS_NAME", "Sheet1"),
            oauth_client_secret_file=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "client_secret.json"),
        ),
        meta=MetaConfig(
            access_token=os.getenv("META_ACCESS_TOKEN", ""),
            facebook_page_id=os.getenv("FACEBOOK_PAGE_ID", ""),
            instagram_account_id=os.getenv("INSTAGRAM_ACCOUNT_ID", ""),
        ),
        scheduler=SchedulerConfig(
            check_interval_minutes=int(os.getenv("POST_CHECK_INTERVAL_MINUTES", "5")),
            timezone=os.getenv("TIMEZONE", "Asia/Damascus"),
        ),
    )


# Global config instance
config = load_config()
