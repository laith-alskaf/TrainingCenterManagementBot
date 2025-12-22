"""
MongoDB Atlas connection and database setup.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB Atlas connection manager."""
    
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls, uri: str, database_name: str = "training_center") -> None:
        """
        Connect to MongoDB Atlas.
        
        Args:
            uri: MongoDB connection string
            database_name: Name of the database to use
        """
        if cls._client is not None:
            logger.warning("MongoDB client already connected")
            return
        
        try:
            cls._client = AsyncIOMotorClient(uri)
            cls._database = cls._client[database_name]
            
            # Verify connection
            await cls._client.admin.command('ping')
            logger.info(f"Connected to MongoDB Atlas: {database_name}")
            
            # Create indexes
            await cls._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def _create_indexes(cls) -> None:
        """Create necessary indexes for collections."""
        if cls._database is None:
            return
        
        # Students: unique telegram_id
        await cls._database.students.create_index("telegram_id", unique=True)
        
        # Registrations: compound index for student+course
        await cls._database.registrations.create_index(
            [("student_id", 1), ("course_id", 1)],
            unique=True
        )
        
        # User preferences: unique telegram_id
        await cls._database.user_preferences.create_index("telegram_id", unique=True)
        
        # Scheduled posts: status index for querying pending
        await cls._database.scheduled_posts.create_index("status")
        
        logger.info("MongoDB indexes created")
    
    @classmethod
    async def disconnect(cls) -> None:
        """Disconnect from MongoDB."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._database = None
            logger.info("Disconnected from MongoDB")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if cls._database is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return cls._database
    
    @classmethod
    def get_collection(cls, name: str):
        """Get a collection by name."""
        return cls.get_database()[name]
