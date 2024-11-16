import logging
import os
from typing import Any, Awaitable, Optional

import redis

log = logging.getLogger("rich")


class AudioCache:
    def __init__(self):
        self.redis = redis.Redis(
            host="quartzbot-redict", port=6379, decode_responses=False  # For binary data
        )
        # Separate client for string data
        self.redis_str = redis.Redis(
            host="quartzbot-redict", port=6379, decode_responses=True  # For string data
        )
        # Create temp directory in the mounted volume
        self.temp_dir = "/tmp/audio"
        os.makedirs(self.temp_dir, exist_ok=True)

    def get_audio(self, video_id: str) -> Awaitable[Any] | None:
        """Get cached audio data & title if it exists"""
        audio_data = self.redis.get(f"audio:{video_id}")
        if audio_data:
            log.info(f"[bright_green]Cache hit for video {video_id}[/]")
        else:
            log.info(f"[yellow]Cache miss for video {video_id}[/]")
        return audio_data

    def get_title(self, video_id: str) -> Optional[str]:
        """Get cached title if it exists"""
        return self.redis_str.get(f"title:{video_id}")

    def cache_audio(self, video_id: str, audio_data: bytes, ttl: int = 3600):
        """Cache audio data with TTL (default 1 hour)"""
        self.redis.set(f"audio:{video_id}", value=audio_data)
        log.info(f"Cached audio for video {video_id}")

    def cache_title(self, video_id: str, title: str, ttl: int = 3600):
        """Cache title with TTL (default 1 hour)"""
        self.redis_str.set(f"title:{video_id}", value=title)

    def clear_cache(self):
        """Clear all cached data"""
        for key in self.redis.scan_iter("audio:*"):
            self.redis.delete(key)
        for key in self.redis_str.scan_iter("title:*"):
            self.redis_str.delete(key)
