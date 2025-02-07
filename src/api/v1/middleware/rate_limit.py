from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict
from typing import Dict, List

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 5, window_seconds: int = 1):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        
    async def dispatch(self, request: Request, call_next):
        instance_id = request.path_params.get("instance_id")
        if not instance_id:
            return await call_next(request)
            
        now = time.time()
        
        # Clean old requests
        self.requests[instance_id] = [
            req_time for req_time in self.requests[instance_id]
            if now - req_time < self.window_seconds
        ]
        
        # Check rate limit
        if len(self.requests[instance_id]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} second(s)"
            )
            
        # Add current request
        self.requests[instance_id].append(now)
        
        # Execute request
        response = await call_next(request)
        return response
