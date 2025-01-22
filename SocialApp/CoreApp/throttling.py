from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
import time
class CustomRateLimiter(BaseThrottle):
    scope = 'custom'

    def allow_request(self, request, view):
        # Implement your custom rate-limiting logic here
        # Return True if the request is allowed, False otherwise
        user_ip = self.get_ident(request)
        if self.is_allowed(user_ip):
            return True
        return False

    def is_allowed(self, user_ip):
        # Custom logic to check if the IP is rate-limited
        # For example, you could use a dictionary or database to track requests
        # Replace with your actual logic
        return True  # Allow all requests for demonstration

    def wait(self):
        # Optionally, return the time (in seconds) to wait before retrying
        return None

    
class TokenRateLimiter(BaseThrottle):
    scope = 'token'

    def allow_request(self, request, view):
        # Extract token from the request (assuming token is in the headers)
        return True

    def is_allowed(self, token):
        # Define custom rate limit (e.g., 100 requests per minute per token)
        limit = 100
        window = 60  # seconds

        cache_key = f"throttle_token_{token}"
        request_timestamps = cache.get(cache_key, [])

        # Filter timestamps within the time window
        current_time = time.time()
        request_timestamps = [
            ts for ts in request_timestamps if current_time - ts < window
        ]

        # Check if the token exceeds the rate limit
        if len(request_timestamps) >= limit:
            return False

        # Add the current request timestamp and update the cache
        request_timestamps.append(current_time)
        cache.set(cache_key, request_timestamps, timeout=window)
        return True

    def wait(self):
        # Optionally return the time to wait before retrying
        return 60  # Wait 60 seconds before retrying