#!/usr/bin/env python3
# Copyright (C) 2026 ForgeRSS Contributors
# Licensed under AGPL-3.0

"""
Base class for RSS feed generators.
Supports both JSON cache (GitHub) and SQLite storage (local/Docker).
"""

import json
import logging
import sqlite3
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytz
from feedgen.feed import FeedGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def is_valid_cover_image(url: str) -> bool:
    """
    Check if URL is a valid cover image (not a tracking pixel or ad).
    """
    if not url:
        return False
    
    # Blacklist tracking/ad domains
    blacklist_domains = [
        'adsrvr.org', 'doubleclick.net', 'googlesyndication.com',
        'googleadservices.com', 'facebook.com/tr', 'analytics',
        'pixel', 'tracker', 'beacon', 'ads.', 'ad.', 'track.',
        'match.', 'sync.', 'cm.', 'ida.', 'ib.', 'cdn-cgi',
    ]
    url_lower = url.lower()
    for domain in blacklist_domains:
        if domain in url_lower:
            return False
    
    # Must have image extension or be from known image paths
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
    has_extension = any(ext in url_lower for ext in valid_extensions)
    
    # Check for common image path patterns
    image_patterns = ['/images/', '/assets/', '/uploads/', '/media/', '/content/', '/img/']
    has_image_path = any(p in url_lower for p in image_patterns)
    
    # Allow if has valid extension OR is from image path
    return has_extension or has_image_path


def stable_fallback_date(identifier: str) -> datetime:
    """Generate stable date from URL hash when date extraction fails."""
    hash_val = abs(hash(identifier)) % 365
    epoch = datetime(2024, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
    return epoch + timedelta(days=hash_val)


@dataclass
class Article:
    """Standard article data model."""
    url: str
    title: str
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    images: list[str] = field(default_factory=list)
    media: list[dict] = field(default_factory=list)
    category: Optional[str] = None
    
    @property
    def url_hash(self) -> str:
        """Generate unique hash from URL for deduplication."""
        return hashlib.md5(self.url.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        data = asdict(self)
        if self.published_at:
            data["published_at"] = self.published_at.isoformat()
        data["url_hash"] = self.url_hash
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create from dict."""
        data = data.copy()
        data.pop("url_hash", None)
        if data.get("published_at") and isinstance(data["published_at"], str):
            try:
                data["published_at"] = datetime.fromisoformat(data["published_at"])
            except ValueError:
                data["published_at"] = None
        return cls(**data)


class BaseFeedGenerator(ABC):
    """
    Abstract base class for RSS feed generators.
    
    Features:
    - Dual storage: JSON cache (GitHub) + SQLite (local/Docker)
    - Automatic deduplication by URL
    - Configurable article limits
    - RSS 2.0 feed generation
    """
    
    # Override in subclasses
    FEED_NAME: str = ""
    FEED_TITLE: str = ""
    FEED_URL: str = ""
    FEED_DESCRIPTION: str = ""
    FEED_LANGUAGE: str = "en"
    FEED_LOGO: Optional[str] = None
    
    # Fetch configuration
    REQUIRE_JS: bool = False  # Set True if site needs JS rendering
    CONTENT_CHECK: str = None  # String to verify fetch success
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.cache_dir = self.base_dir / "cache"
        self.feeds_dir = self.base_dir / "feeds"
        self.db_path = self.base_dir / "data" / "forgerss.db"
        
        self.cache_dir.mkdir(exist_ok=True)
        self.feeds_dir.mkdir(exist_ok=True)
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize SQLite if enabled
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feed_name TEXT NOT NULL,
                    url_hash TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    published_at TEXT,
                    summary TEXT,
                    content TEXT,
                    author TEXT,
                    images TEXT,
                    media TEXT,
                    category TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(feed_name, url_hash)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_name ON articles(feed_name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_published ON articles(feed_name, published_at DESC)
            """)
            conn.commit()
            conn.close()
            self.logger.debug("SQLite initialized")
        except Exception as e:
            self.logger.warning(f"SQLite init failed: {e}, using JSON only")
    
    # ========== Storage: JSON Cache ==========
    
    @property
    def cache_file(self) -> Path:
        return self.cache_dir / f"{self.FEED_NAME}.json"
    
    def load_cache(self) -> list[Article]:
        """Load articles from JSON cache."""
        if not self.cache_file.exists():
            return []
        
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            articles = [Article.from_dict(a) for a in data.get("articles", [])]
            self.logger.info(f"Loaded {len(articles)} articles from cache")
            return articles
        except Exception as e:
            self.logger.error(f"Failed to load cache: {e}")
            return []
    
    def save_cache(self, articles: list[Article]):
        """Save articles to JSON cache."""
        data = {
            "feed_name": self.FEED_NAME,
            "last_updated": datetime.now(pytz.UTC).isoformat(),
            "count": len(articles),
            "articles": [a.to_dict() for a in articles]
        }
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(articles)} articles to cache")
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
    
    # ========== Storage: SQLite ==========
    
    def load_from_db(self, limit: int = 100) -> list[Article]:
        """Load articles from SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM articles 
                WHERE feed_name = ? 
                ORDER BY published_at DESC 
                LIMIT ?
            """, (self.FEED_NAME, limit))
            
            articles = []
            for row in cursor:
                data = dict(row)
                data.pop("id", None)
                data.pop("feed_name", None)
                data.pop("created_at", None)
                data["images"] = json.loads(data.get("images") or "[]")
                data["media"] = json.loads(data.get("media") or "[]")
                articles.append(Article.from_dict(data))
            
            conn.close()
            self.logger.info(f"Loaded {len(articles)} articles from DB")
            return articles
        except Exception as e:
            self.logger.warning(f"Failed to load from DB: {e}")
            return []
    
    def save_to_db(self, articles: list[Article]):
        """Save articles to SQLite database (upsert)."""
        try:
            conn = sqlite3.connect(self.db_path)
            for article in articles:
                conn.execute("""
                    INSERT OR REPLACE INTO articles 
                    (feed_name, url_hash, url, title, published_at, summary, 
                     content, author, images, media, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.FEED_NAME,
                    article.url_hash,
                    article.url,
                    article.title,
                    article.published_at.isoformat() if article.published_at else None,
                    article.summary,
                    article.content,
                    article.author,
                    json.dumps(article.images),
                    json.dumps(article.media),
                    article.category
                ))
            conn.commit()
            conn.close()
            self.logger.info(f"Saved {len(articles)} articles to DB")
        except Exception as e:
            self.logger.warning(f"Failed to save to DB: {e}")
    
    def get_existing_urls(self) -> set[str]:
        """Get all existing article URLs from DB for deduplication."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT url FROM articles WHERE feed_name = ?", 
                (self.FEED_NAME,)
            )
            urls = {row[0] for row in cursor}
            conn.close()
            return urls
        except Exception:
            return set()
    
    # ========== Deduplication ==========
    
    def merge_articles(
        self, 
        new_articles: list[Article], 
        existing: list[Article]
    ) -> list[Article]:
        """
        Merge new articles with existing, deduplicate by URL.
        Returns sorted list (newest first).
        """
        existing_urls = {a.url for a in existing}
        merged = list(existing)
        
        added = 0
        for article in new_articles:
            if article.url not in existing_urls:
                merged.append(article)
                existing_urls.add(article.url)
                added += 1
        
        self.logger.info(f"Added {added} new articles")
        
        # Sort by date (newest first)
        merged.sort(
            key=lambda a: a.published_at or datetime.min.replace(tzinfo=pytz.UTC),
            reverse=True
        )
        
        return merged
    
    # ========== RSS Generation ==========
    
    def generate_rss(self, articles: list[Article]) -> FeedGenerator:
        """Generate RSS 2.0 feed using feedgen (kept for compatibility)."""
        fg = FeedGenerator()
        fg.title(self.FEED_TITLE)
        fg.description(self.FEED_DESCRIPTION)
        fg.link(href=self.FEED_URL, rel="alternate")
        fg.language(self.FEED_LANGUAGE)
        if self.FEED_LOGO:
            fg.logo(self.FEED_LOGO)
        return fg
    
    def save_feed(self, fg: FeedGenerator, articles: list[Article] = None) -> Path:
        """
        Save RSS feed with CDATA-wrapped content for maximum compatibility.
        References wechatrss style for Readwise Reader and other readers.
        """
        from xml.dom import minidom
        from html import escape as html_escape
        
        if articles is None:
            articles = []
        
        # Sort by date
        sorted_articles = sorted(
            articles,
            key=lambda a: a.published_at or datetime.min.replace(tzinfo=pytz.UTC),
            reverse=True
        )
        
        doc = minidom.Document()
        rss = doc.createElement("rss")
        rss.setAttribute("version", "2.0")
        rss.setAttribute("xmlns:atom", "http://www.w3.org/2005/Atom")
        rss.setAttribute("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
        doc.appendChild(rss)
        
        channel = doc.createElement("channel")
        rss.appendChild(channel)
        
        def add_text(parent, tag: str, text: str):
            elem = doc.createElement(tag)
            elem.appendChild(doc.createTextNode(str(text)))
            parent.appendChild(elem)
            return elem
        
        add_text(channel, "title", self.FEED_TITLE)
        add_text(channel, "link", self.FEED_URL)
        add_text(channel, "description", self.FEED_DESCRIPTION)
        add_text(channel, "language", self.FEED_LANGUAGE)
        add_text(channel, "lastBuildDate", 
                 datetime.now(pytz.UTC).strftime("%a, %d %b %Y %H:%M:%S +0000"))
        add_text(channel, "generator", "ForgeRSS")
        
        # Feed logo/image
        if self.FEED_LOGO:
            image = doc.createElement("image")
            add_text(image, "url", self.FEED_LOGO)
            add_text(image, "title", self.FEED_TITLE)
            add_text(image, "link", self.FEED_URL)
            channel.appendChild(image)
        
        # Build items
        for article in sorted_articles:
            item = doc.createElement("item")
            
            add_text(item, "title", article.title)
            add_text(item, "link", article.url)
            
            guid = doc.createElement("guid")
            guid.setAttribute("isPermaLink", "false")
            guid.appendChild(doc.createTextNode(article.url))
            item.appendChild(guid)
            
            if article.published_at:
                add_text(item, "pubDate", 
                        article.published_at.strftime("%a, %d %b %Y %H:%M:%S +0000"))
            
            if article.author:
                add_text(item, "author", article.author)
            
            if article.category:
                add_text(item, "category", article.category)
            
            # Filter out tracking pixels and get valid cover image
            valid_images = [img for img in article.images if is_valid_cover_image(img)]
            cover = valid_images[0] if valid_images else None
            
            # Build HTML content (same for description and content:encoded)
            # Following wechatrss pattern: use full content if available
            html_parts = []
            
            if article.content:
                # Has full content - show it directly
                html_parts.append(
                    f'<div style="font-size:16px;line-height:1.8;color:#333">'
                    f'{article.content}</div>'
                )
                if article.author:
                    html_parts.append(
                        f'<hr style="margin:24px 0;border:none;border-top:1px solid #eee" />'
                        f'<p style="color:#888;font-size:13px;margin:0">Author: {html_escape(article.author)}</p>'
                    )
            else:
                # No full content - show cover + summary + read link
                if cover:
                    html_parts.append(
                        f'<div style="margin-bottom:12px">'
                        f'<a href="{html_escape(article.url)}">'
                        f'<img src="{html_escape(cover)}" alt="{html_escape(article.title)}" '
                        f'style="max-width:100%;height:auto;border-radius:8px" /></a></div>'
                    )
                if article.summary:
                    html_parts.append(
                        f'<p style="color:#333;font-size:15px;line-height:1.8;margin:0 0 16px">'
                        f'{html_escape(article.summary)}</p>'
                    )
                if article.author:
                    html_parts.append(
                        f'<p style="color:#888;font-size:13px;margin:0 0 12px">'
                        f'Author: {html_escape(article.author)}</p>'
                    )
                html_parts.append(
                    f'<p style="margin:0"><a href="{html_escape(article.url)}" '
                    f'style="color:#1890ff;text-decoration:none;font-size:14px">'
                    f'Read full article &rarr;</a></p>'
                )
            
            content_html = "\n".join(html_parts)
            
            # description (CDATA wrapped)
            description = doc.createElement("description")
            description.appendChild(doc.createCDATASection(content_html))
            item.appendChild(description)
            
            # content:encoded (same content, CDATA wrapped)
            content_encoded = doc.createElement("content:encoded")
            content_encoded.appendChild(doc.createCDATASection(content_html))
            item.appendChild(content_encoded)
            
            # Enclosure for cover image
            if cover:
                enclosure = doc.createElement("enclosure")
                enclosure.setAttribute("url", cover)
                mime = "image/jpeg"
                if cover.endswith(".png"):
                    mime = "image/png"
                elif cover.endswith(".gif"):
                    mime = "image/gif"
                elif cover.endswith(".webp"):
                    mime = "image/webp"
                enclosure.setAttribute("type", mime)
                enclosure.setAttribute("length", "0")
                item.appendChild(enclosure)
            
            channel.appendChild(item)
        
        # Write to file
        output = self.feeds_dir / f"feed_{self.FEED_NAME}.xml"
        xml_str = doc.toprettyxml(indent="  ", encoding=None)
        # Clean up XML declaration line
        lines = [line for line in xml_str.split('\n') if line.strip()]
        xml_str = '\n'.join(lines[1:])  # Skip default xml declaration
        final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        with open(output, "w", encoding="utf-8") as f:
            f.write(final_xml)
        
        self.logger.info(f"Saved feed to {output}")
        return output
    
    # ========== Abstract Methods ==========
    
    @abstractmethod
    def fetch_articles(self) -> list[Article]:
        """
        Fetch article list from source.
        Must be implemented by subclasses.
        """
        pass
    
    def fetch_article_content(self, url: str) -> Optional[Article]:
        """
        Fetch full article content (optional).
        Override if you need to fetch article details.
        """
        return None
    
    # ========== Main Entry ==========
    
    def run(
        self, 
        full_refresh: bool = False, 
        max_articles: int = 50,
        use_db: bool = True
    ) -> bool:
        """
        Main entry point.
        
        Args:
            full_refresh: Ignore cache, fetch all
            max_articles: Max articles to keep
            use_db: Use SQLite storage (in addition to JSON)
        
        Returns:
            True on success
        """
        try:
            # Load existing
            if full_refresh:
                existing = []
            else:
                existing = self.load_cache()
                if not existing and use_db:
                    existing = self.load_from_db(limit=max_articles)
            
            # Fetch new
            self.logger.info(f"Fetching articles from {self.FEED_URL}")
            new_articles = self.fetch_articles()
            
            if not new_articles:
                self.logger.warning("No articles fetched")
                if existing:
                    # Use existing for RSS
                    fg = self.generate_rss(existing[:max_articles])
                    self.save_feed(fg, existing[:max_articles])
                return len(existing) > 0
            
            # Fetch content for new articles (optional)
            for i, article in enumerate(new_articles):
                if article.content is None:
                    detailed = self.fetch_article_content(article.url)
                    if detailed:
                        # Merge: keep original title, prefer detailed date if available
                        # (detailed page often has more accurate date)
                        new_articles[i] = Article(
                            url=article.url,
                            title=article.title,  # Keep original title
                            published_at=detailed.published_at or article.published_at,
                            summary=detailed.summary or article.summary,
                            content=detailed.content,
                            author=detailed.author or article.author,
                            images=detailed.images or article.images,
                            media=detailed.media or article.media,
                            category=article.category or detailed.category,
                        )
            
            # Merge and deduplicate
            merged = self.merge_articles(new_articles, existing)
            final = merged[:max_articles]
            
            # Save
            self.save_cache(final)
            if use_db:
                self.save_to_db(final)
            
            # Generate RSS
            fg = self.generate_rss(final)
            self.save_feed(fg, final)
            
            self.logger.info(f"Success: {len(final)} articles in feed")
            return True
            
        except Exception as e:
            self.logger.error(f"Run failed: {e}", exc_info=True)
            return False
