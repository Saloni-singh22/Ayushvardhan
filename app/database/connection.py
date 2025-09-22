"""
Database connection and configuration module
MongoDB setup with Motor async driver for FHIR R4 resources
"""

import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi
import logging

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager with async support"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """Establish connection to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.mongodb_max_connections,
                minPoolSize=settings.mongodb_min_connections,
                server_api=ServerApi('1'),
                # Connection timeout settings
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
            )
            
            # Test the connection
            await self.client.admin.command('ping')
            self.database = self.client[settings.mongodb_database]
            
            logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
            
            # Create indexes for optimal performance
            await self.create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def create_indexes(self) -> None:
        """Create database indexes for optimal terminology searches"""
        try:
            # FHIR CodeSystem collection indexes
            await self.database.codesystems.create_index([
                ("url", 1),
                ("version", 1)
            ], unique=True, name="codesystem_url_version")
            
            # Try to create text search index, skip if it fails due to data issues
            try:
                await self.database.codesystems.create_index([
                    ("name", "text"),
                    ("title", "text"),
                    ("concept.display", "text")
                ], name="codesystem_text_search")
            except Exception as text_index_error:
                if "language override field" in str(text_index_error):
                    logger.warning("Skipping text search index creation due to language field issues. Text search will be limited.")
                else:
                    logger.error(f"Failed to create text search index: {text_index_error}")
            
            await self.database.codesystems.create_index([
                ("status", 1),
                ("date", -1)
            ], name="codesystem_status_date")
            
            # FHIR ConceptMap collection indexes
            await self.database.conceptmaps.create_index([
                ("url", 1),
                ("version", 1)
            ], unique=True, name="conceptmap_url_version")
            
            await self.database.conceptmaps.create_index([
                ("sourceUri", 1),
                ("targetUri", 1)
            ], name="conceptmap_source_target")
            
            await self.database.conceptmaps.create_index([
                ("group.element.code", 1),
                ("group.source", 1)
            ], name="conceptmap_code_search")
            
            # FHIR ValueSet collection indexes
            await self.database.valuesets.create_index([
                ("url", 1),
                ("version", 1)
            ], unique=True, name="valueset_url_version")
            
            await self.database.valuesets.create_index([
                ("compose.include.system", 1),
                ("compose.include.concept.code", 1)
            ], name="valueset_system_code")
            
            # NAMASTE codes collection indexes
            await self.database.namaste_codes.create_index([
                ("code", 1),
                ("system", 1)
            ], unique=True, name="namaste_code_system")
            
            await self.database.namaste_codes.create_index([
                ("display", "text"),
                ("definition", "text"),
                ("designation.value", "text")
            ], name="namaste_text_search")
            
            await self.database.namaste_codes.create_index([
                ("system", 1),
                ("status", 1)
            ], name="namaste_system_status")
            
            # WHO ICD-11 codes collection indexes
            await self.database.who_icd_codes.create_index([
                ("code", 1),
                ("release", 1),
                ("linearization", 1)
            ], unique=True, name="who_icd_code_release_linear")
            
            await self.database.who_icd_codes.create_index([
                ("title.@value", "text"),
                ("definition.@value", "text")
            ], name="who_icd_text_search")
            
            await self.database.who_icd_codes.create_index([
                ("parent", 1),
                ("child", 1)
            ], name="who_icd_hierarchy")
            
            # Code mappings collection indexes
            await self.database.code_mappings.create_index([
                ("source_code", 1),
                ("source_system", 1),
                ("target_system", 1)
            ], name="mapping_source_target")
            
            await self.database.code_mappings.create_index([
                ("confidence_score", -1),
                ("mapping_type", 1)
            ], name="mapping_confidence_type")
            
            # ABHA authentication collection indexes
            await self.database.abha_sessions.create_index([
                ("abha_number", 1)
            ], unique=True, name="abha_number_unique")
            
            await self.database.abha_sessions.create_index([
                ("access_token", 1)
            ], name="abha_access_token")
            
            await self.database.abha_sessions.create_index([
                ("expires_at", 1)
            ], expireAfterSeconds=0, name="abha_session_expiry")
            
            # Audit trail collection indexes
            await self.database.audit_logs.create_index([
                ("timestamp", -1),
                ("user_id", 1)
            ], name="audit_timestamp_user")
            
            await self.database.audit_logs.create_index([
                ("action", 1),
                ("resource_type", 1)
            ], name="audit_action_resource")
            
            await self.database.audit_logs.create_index([
                ("consent_id", 1)
            ], name="audit_consent")
            
            # Performance monitoring collection indexes
            await self.database.performance_metrics.create_index([
                ("timestamp", -1)
            ], name="metrics_timestamp")
            
            await self.database.performance_metrics.create_index([
                ("endpoint", 1),
                ("method", 1)
            ], name="metrics_endpoint_method")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database indexes: {e}")
            # Don't raise here as the application can still function
    
    async def get_collection_stats(self) -> dict:
        """Get database collection statistics"""
        try:
            stats = {}
            collections = await self.database.list_collection_names()
            
            for collection_name in collections:
                collection = self.database[collection_name]
                count = await collection.count_documents({})
                stats[collection_name] = {"document_count": count}
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global MongoDB instance
mongodb = MongoDB()


async def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance"""
    if mongodb.database is None:
        await mongodb.connect()
    return mongodb.database


async def init_database() -> None:
    """Initialize database connection"""
    await mongodb.connect()


async def close_database() -> None:
    """Close database connection"""
    await mongodb.disconnect()


# Database connection event handlers for FastAPI
async def startup_database():
    """Database startup event handler"""
    await init_database()
    logger.info("Database connection established")


async def shutdown_database():
    """Database shutdown event handler"""
    await close_database()
    logger.info("Database connection closed")