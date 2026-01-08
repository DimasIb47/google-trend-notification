"""Parser for Google Trends batchexecute response."""

import json
import re
import logging
from typing import List, Optional
from datetime import datetime

from .models import TrendItem

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """
    Normalize a trend title for deduplication.
    
    Rules:
    - Convert to lowercase
    - Strip leading/trailing whitespace
    - Collapse multiple spaces to single space
    - Remove zero-width and invisible Unicode characters
    """
    if not title:
        return ""

    # Remove zero-width and invisible characters
    title = re.sub(r'[\u200b-\u200f\u2028-\u202f\ufeff\u00ad]', '', title)

    # Normalize unicode (NFKC form)
    import unicodedata
    title = unicodedata.normalize('NFKC', title)

    # Lowercase
    title = title.lower()

    # Collapse multiple spaces
    title = ' '.join(title.split())

    return title.strip()


def parse_batchexecute_response(raw_response: str, geo: str) -> List[TrendItem]:
    """
    Parse the batchexecute response and extract trend items.
    
    The response format is:
    - Starts with )]}' prefix
    - Contains length-prefixed JSON chunks
    - The i0OFE chunk contains the trend data
    
    Args:
        raw_response: Raw response text from batchexecute
        geo: Geographic region code
        
    Returns:
        List of TrendItem objects
    """
    trends = []

    try:
        # Remove the security prefix )]}' and any leading characters
        cleaned = raw_response
        if cleaned.startswith(")]}'"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        # Split into lines/chunks and find the one with i0OFE data
        # The format is: NUMBER\nJSON_ARRAY\nNUMBER\nJSON_ARRAY...
        lines = cleaned.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.isdigit():
                continue

            try:
                # Try to parse as JSON
                parsed = json.loads(line)

                # Look for the i0OFE response
                # Format: [["wrb.fr","i0OFE","[DATA]",null,null,null,"generic"]]
                if isinstance(parsed, list) and len(parsed) > 0:
                    for item in parsed:
                        if isinstance(item, list) and len(item) >= 3:
                            if item[0] == "wrb.fr" and item[1] == "i0OFE":
                                data_str = item[2]
                                if data_str:
                                    trends = _parse_trends_data(data_str, geo)
                                    if trends:
                                        logger.info(f"Parsed {len(trends)} trends for {geo}")
                                        return trends

            except json.JSONDecodeError:
                continue

        # If we couldn't find i0OFE in the structured way, try regex
        logger.debug("Falling back to regex parsing")
        trends = _parse_with_regex(raw_response, geo)

    except Exception as e:
        logger.error(f"Error parsing response for {geo}: {e}")

    return trends


def _parse_trends_data(data_str: str, geo: str) -> List[TrendItem]:
    """Parse the inner trends data string."""
    trends = []

    try:
        data = json.loads(data_str)

        # The structure is: [null, [[trend1], [trend2], ...]]
        # Or variations like: [null, [[[trend1], [trend2], ...]]]
        if not isinstance(data, list) or len(data) < 2:
            return trends

        # Navigate to the trends array
        trends_array = None

        # Try different possible structures
        if isinstance(data[1], list):
            if len(data[1]) > 0 and isinstance(data[1][0], list):
                if len(data[1][0]) > 0 and isinstance(data[1][0][0], list):
                    # Structure: [null, [[[trend], [trend], ...]]]
                    trends_array = data[1][0]
                else:
                    # Structure: [null, [[trend], [trend], ...]]
                    trends_array = data[1]

        if not trends_array:
            logger.warning(f"Could not find trends array in data for {geo}")
            return trends

        for idx, trend_data in enumerate(trends_array):
            try:
                trend = _parse_single_trend(trend_data, geo, idx + 1)
                if trend:
                    trends.append(trend)
            except Exception as e:
                logger.debug(f"Error parsing trend {idx}: {e}")
                continue

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in trends data: {e}")
    except Exception as e:
        logger.error(f"Error parsing trends data: {e}")

    return trends


def _parse_single_trend(trend_data: list, geo: str, rank: int) -> Optional[TrendItem]:
    """Parse a single trend from the array."""
    if not isinstance(trend_data, list) or len(trend_data) < 2:
        return None

    # Extract fields based on typical structure
    # Index positions may vary, so we try multiple approaches
    title = None
    search_volume = ""
    growth_percent = ""
    started_time = ""
    status = "Active"
    duration = ""
    related_queries = []

    # Try to extract title (usually at index 0 or 1)
    for i in range(min(3, len(trend_data))):
        if isinstance(trend_data[i], str) and len(trend_data[i]) > 1:
            title = trend_data[i]
            break

    if not title:
        return None

    # Try to extract other fields
    for item in trend_data:
        if isinstance(item, str):
            # Search volume pattern: "500+", "1K+", "2M+"
            if re.match(r'^\d+[KMB]?\+?$', item) or re.match(r'^[\d,]+\+?$', item):
                if not search_volume:
                    search_volume = item
            # Growth pattern: "+200%", "↑ 200%"
            elif re.match(r'^[+↑]\s?\d+%$', item) or item.endswith('%'):
                if not growth_percent:
                    growth_percent = item
            # Time pattern: "X hours ago", "X minutes ago"
            elif 'ago' in item.lower():
                if not started_time:
                    started_time = item
            # Duration pattern: "Lasted X hrs"
            elif 'lasted' in item.lower():
                if not duration:
                    duration = item
            # Status
            elif item.lower() in ('active', 'ended'):
                status = item.capitalize()

        elif isinstance(item, list):
            # Could be related queries or articles
            for sub_item in item:
                if isinstance(sub_item, str) and len(sub_item) > 2:
                    related_queries.append(sub_item)

    return TrendItem(
        title=title,
        normalized_title=normalize_title(title),
        rank=rank,
        search_volume=search_volume,
        growth_percent=growth_percent,
        started_time=started_time,
        status=status,
        duration=duration,
        geo=geo,
        related_queries=related_queries[:5],  # Limit to 5
    )


def _parse_with_regex(raw_response: str, geo: str) -> List[TrendItem]:
    """Fallback regex-based parsing for edge cases."""
    trends = []

    # Try to find the data string for i0OFE
    pattern = r'\["wrb\.fr","i0OFE","(.+?)(?:(?<!\\)"(?:,null)*,"generic")'
    match = re.search(pattern, raw_response, re.DOTALL)

    if match:
        data_str = match.group(1)
        # Unescape the JSON string
        data_str = data_str.replace('\\"', '"').replace('\\\\', '\\')
        trends = _parse_trends_data(data_str, geo)

    return trends
