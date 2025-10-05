"""Redis pub/sub publisher for WebSocket progress updates"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import redis.asyncio as aioredis

from ..config import settings
from ..utils.json_encoder import json_dumps

logger = logging.getLogger(__name__)


class RedisPublisher:
    """Redis publisher for WebSocket progress updates"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._client: Optional[aioredis.Redis] = None
    
    async def get_client(self) -> aioredis.Redis:
        """Get or create Redis client"""
        if self._client is None:
            self._client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._client
    
    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def publish_progress(
        self,
        query_id: str,
        stage: str,
        message: str,
        message_type: str = "PROGRESS",
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Publish progress update to Redis channel.
        
        Args:
            query_id: Query ID to publish to
            stage: Current workflow stage
            message: Human-readable progress message
            message_type: Type of message (PROGRESS, SQL_GENERATED, etc.)
            extra_data: Additional data to include in message
        """
        try:
            client = await self.get_client()
            channel = f"query_status_{query_id}"
            
            payload = {
                "type": message_type,
                "queryId": query_id,
                "stage": stage,
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # Add extra data if provided
            if extra_data:
                payload.update(extra_data)
            
            # Publish to channel (use custom encoder to handle Decimal and other types)
            await client.publish(channel, json_dumps(payload))
            
            logger.debug(f"Published {message_type} to {channel}: {message}")
            
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")
            # Don't raise - progress updates are non-critical
    
    async def publish_sql_generated(self, query_id: str, sql_query: str):
        """
        Publish SQL generated message.
        
        Args:
            query_id: Query ID
            sql_query: Generated SQL query
        """
        await self.publish_progress(
            query_id=query_id,
            stage="sql_generated",
            message="SQL query generated successfully",
            message_type="SQL_GENERATED",
            extra_data={"sqlQuery": sql_query}
        )
    
    async def publish_completed(self, query_id: str, result: Dict[str, Any]):
        """
        Publish query completion message.
        
        Args:
            query_id: Query ID
            result: Final result (ChartGenerationResult)
        """
        await self.publish_progress(
            query_id=query_id,
            stage="completed",
            message="Query completed successfully",
            message_type="COMPLETED",
            extra_data={"result": result}
        )
    
    async def publish_error(self, query_id: str, error: Dict[str, Any]):
        """
        Publish error message.
        
        Args:
            query_id: Query ID
            error: Error details (ChartGenerationError)
        """
        await self.publish_progress(
            query_id=query_id,
            stage="error",
            message=error.get("error", "An error occurred"),
            message_type="ERROR",
            extra_data={"error": error}
        )


# Global publisher instance
_publisher: Optional[RedisPublisher] = None


async def get_publisher() -> RedisPublisher:
    """Get global Redis publisher instance"""
    global _publisher
    if _publisher is None:
        _publisher = RedisPublisher()
    return _publisher


async def publish_progress(
    query_id: str,
    stage: str,
    message: str,
    message_type: str = "PROGRESS",
    extra_data: Optional[Dict[str, Any]] = None
):
    """
    Convenience function to publish progress.
    
    Args:
        query_id: Query ID
        stage: Current stage
        message: Progress message
        message_type: Message type
        extra_data: Additional data
    """
    publisher = await get_publisher()
    await publisher.publish_progress(
        query_id=query_id,
        stage=stage,
        message=message,
        message_type=message_type,
        extra_data=extra_data
    )

