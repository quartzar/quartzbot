"""Utility functions"""

import logging
from dataclasses import dataclass
from io import BytesIO

import aiohttp

log = logging.getLogger(__name__)

TIME_DURATION_UNITS = (
    ("week", 60 * 60 * 24 * 7),
    ("day", 60 * 60 * 24),
    ("hour", 60 * 60),
    ("min", 60),
    ("sec", 1),
)


@dataclass
class QueueItem:
    video_id: str
    title: str
    requested_by: str
    url: str


def human_time_duration(seconds: int) -> str:
    if seconds == 0:
        return "inf"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append("{} {}{}".format(amount, unit, "" if amount == 1 else "s"))
    return ", ".join(parts)


async def download_image_from_url(url: str) -> BytesIO | None:
    """Asynchronously downloads an image from a URL and returns it as a file-like object.

    :param url: Image URL to download
    :returns: BytesIO object containing the image data, or None if download fails
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                # Raise an exception for bad status codes (4xx or 5xx)
                response.raise_for_status()
                # Read the content and create an in-memory binary stream
                image_bytes = await response.read()
                return BytesIO(image_bytes)
    except aiohttp.ClientError as e:
        print(f"Error downloading image: {e}")
        return None
