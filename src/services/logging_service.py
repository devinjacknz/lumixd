import logging
import json
import os
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from typing import Dict, Any, Optional, List

class LoggingService:
    def __init__(self):
        # Configure file logging with rotation
        os.makedirs('logs', exist_ok=True)
        
        # Configure rotating file handler
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            filename='logs/user_operations.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)
        
        # MongoDB setup for persistent storage
        self.mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.db_name = os.getenv('MONGODB_DB', 'lumixd')
        self.mongo_client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.mongo_client[self.db_name]
        self.user_logs = self.db.user_logs
        
        # Redis setup for real-time updates
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(self.redis_url)
        
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from log data"""
        sensitive_keys = ['private_key', 'wallet_key', 'secret', 'password', 'key']
        sanitized = {}
        
        def sanitize_value(value: Any) -> Any:
            if isinstance(value, dict):
                return self._sanitize_data(value)
            elif isinstance(value, list):
                return [sanitize_value(v) for v in value]
            elif isinstance(value, str) and len(value) > 32:
                return f"{value[:4]}...{value[-4:]}"
            return value
            
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_value(value)
                
        return sanitized
        
    async def _log_to_file(self, action_type: str, user_id: Optional[str], data: Dict[str, Any]) -> None:
        """Log to file with rotation"""
        try:
            logging.info(f"User Action: {action_type} - User: {user_id} - Data: {json.dumps(data)}")
        except Exception as e:
            logging.error(f"File logging error: {str(e)}")
            
    async def _log_to_mongodb(self, log_entry: Dict[str, Any]) -> None:
        """Log to MongoDB with error handling"""
        if self.user_logs:
            try:
                await self.user_logs.insert_one(log_entry)
            except Exception as e:
                logging.error(f"MongoDB logging error: {str(e)}")
                
    async def _log_to_redis(self, timestamp: datetime, action_type: str, user_id: Optional[str], data: Dict[str, Any]) -> None:
        """Log to Redis with error handling"""
        if self.redis_client:
            try:
                await self.redis_client.lpush(
                    'recent_user_actions',
                    json.dumps({
                        'timestamp': timestamp.isoformat(),
                        'action_type': action_type,
                        'user_id': user_id,
                        'data': data,
                        'env': os.getenv('FLASK_ENV', 'development')
                    })
                )
                await self.redis_client.ltrim('recent_user_actions', 0, 999)
            except Exception as e:
                logging.error(f"Redis logging error: {str(e)}")
    
    async def log_user_action(self, action_type: str, data: Dict[str, Any], user_id: Optional[str] = None) -> None:
        """Log user action to both MongoDB and Redis with data sanitization"""
        try:
            timestamp = datetime.utcnow()
            sanitized_data = self._sanitize_data(data)
            
            log_entry = {
                'timestamp': timestamp,
                'action_type': action_type,
                'user_id': user_id,
                'data': sanitized_data,
                'source': 'defi_agent',
                'env': os.getenv('FLASK_ENV', 'development')
            }
            
            # Parallel logging to all destinations
            await asyncio.gather(
                self._log_to_file(action_type, user_id, sanitized_data),
                self._log_to_mongodb(log_entry),
                self._log_to_redis(timestamp, action_type, user_id, sanitized_data)
            )
        except Exception as e:
            logging.error(f"Error in log_user_action: {str(e)}")
            # Don't raise the exception to prevent API failures due to logging issues
            
    async def get_user_actions(self, user_id: Optional[str] = None, limit: int = 100) -> list:
        """Retrieve user actions from MongoDB"""
        query = {'user_id': user_id} if user_id else {}
        cursor = self.user_logs.find(query).sort('timestamp', -1).limit(limit)
        return await cursor.to_list(length=limit)
        
    async def get_recent_actions(self, limit: int = 100) -> list:
        """Get recent actions from Redis"""
        actions = await self.redis_client.lrange('recent_user_actions', 0, limit - 1)
        return [json.loads(action) for action in actions]
        
    async def log_trade_attempt(self, instruction: str, user_id: Optional[str] = None) -> None:
        """Log trade attempt"""
        await self.log_user_action(
            'trade_attempt',
            {'instruction': instruction},
            user_id
        )
        
    async def log_trade_result(self, result: Dict[str, Any], user_id: Optional[str] = None) -> None:
        """Log trade result"""
        await self.log_user_action(
            'trade_result',
            result,
            user_id
        )
        
    async def log_error(self, error: str, context: Dict[str, Any], user_id: Optional[str] = None) -> None:
        """Log error with context"""
        await self.log_user_action(
            'error',
            {
                'error_message': error,
                'context': context
            },
            user_id
        )

logging_service = LoggingService()  # Singleton instance
