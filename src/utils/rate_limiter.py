"""
Rate Limiter using sliding window algorithm
"""
import time
from collections import deque
from typing import Dict


class RateLimiter:
    """Rate limiter using sliding window algorithm"""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove requests outside the time window
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            # Calculate how long to wait
            oldest_request = self.requests[0]
            wait_time = self.time_window - (now - oldest_request)
            
            if wait_time > 0:
                print(f"⏳ Rate limit reached. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time + 0.1)  # Add small buffer
                
                # Clean up old requests after waiting
                now = time.time()
                while self.requests and self.requests[0] <= now - self.time_window:
                    self.requests.popleft()
        
        # Record this request
        self.requests.append(time.time())
        
    def get_status(self) -> Dict:
        """Get current rate limiter status"""
        now = time.time()
        
        # Clean up old requests
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        remaining = self.max_requests - len(self.requests)
        
        return {
            'requests_made': len(self.requests),
            'max_requests': self.max_requests,
            'remaining': remaining,
            'window_seconds': self.time_window
        }
