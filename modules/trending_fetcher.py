"""
Fetches trending topics and news from Google Trends India + Indian news RSS feeds.
Keeps video content fresh and relevant to current events.
"""

import logging
import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

GOOGLE_TRENDS_INDIA_RSS = "https://trends.google.com/trending/rss?geo=IN"

NEWS_RSS_FEEDS = [
    # English news
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "https://feeds.feedburner.com/ndtvnews-top-stories",
    "https://www.thehindu.com/feeder/default.rss",
    "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    # Hindi news
    "https://feeds.feedburner.com/ndtvkhaber-latest",
    "https://www.bhaskar.com/rss-feed/1061/",
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_trending_topics(max_topics: int = 15) -> list[dict]:
    """
    Returns list of dicts: [{title, description, source}]
    Falls back to empty list if all fetches fail.
    """
    results = []

    # 1. Google Trends India — most viral real-time searches
    try:
        trends = _fetch_google_trends()
        results.extend(trends)
        logger.info(f"Google Trends: fetched {len(trends)} topics")
    except Exception as e:
        logger.warning(f"Google Trends failed: {e}")

    # 2. News RSS feeds — top headlines with context
    for url in NEWS_RSS_FEEDS:
        try:
            headlines = _fetch_rss_feed(url)
            results.extend(headlines)
            logger.info(f"RSS {url.split('/')[2]}: fetched {len(headlines)} topics")
        except Exception as e:
            logger.warning(f"RSS {url} failed: {e}")

    # Deduplicate by title (case-insensitive)
    seen, unique = set(), []
    for item in results:
        key = item["title"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:max_topics]


def _fetch_google_trends() -> list[dict]:
    req = Request(GOOGLE_TRENDS_INDIA_RSS, headers=_HEADERS)
    with urlopen(req, timeout=8) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    items = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        if title_el is None or not title_el.text:
            continue
        title = _clean(title_el.text)

        # Try to grab approximate traffic info
        traffic_el = item.find("{https://trends.google.com/trends/trendingsearches/daily}approx_traffic")
        desc = f"India mein trending search — {traffic_el.text} searches" if (traffic_el is not None and traffic_el.text) else "India mein trending"

        items.append({"title": title, "description": desc, "source": "google_trends"})

    return items[:8]


def _fetch_rss_feed(url: str) -> list[dict]:
    req = Request(url, headers=_HEADERS)
    with urlopen(req, timeout=8) as resp:
        raw = resp.read()

    xml_str = raw.decode("utf-8", errors="replace")
    xml_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', xml_str)

    root = ET.fromstring(xml_str)
    items = []
    source_name = url.split('/')[2].replace("www.", "").replace("feeds.feedburner.com/", "")

    for item in root.findall(".//item")[:6]:
        title_el = item.find("title")
        desc_el  = item.find("description")
        if title_el is None or not title_el.text:
            continue

        title = _clean(title_el.text)
        desc  = _clean(desc_el.text) if (desc_el is not None and desc_el.text) else ""
        # Trim desc to ~200 chars for prompt context
        if len(desc) > 200:
            desc = desc[:197] + "..."

        if len(title) < 10:
            continue

        items.append({"title": title, "description": desc, "source": source_name})

    return items


def _clean(text: str) -> str:
    """Remove HTML tags, CDATA markers, extra whitespace."""
    text = re.sub(r'<!\[CDATA\[|\]\]>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    return text.strip()
