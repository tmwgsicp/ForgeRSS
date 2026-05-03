#!/usr/bin/env python3
# Copyright (c) 2026 ForgeRSS Contributors
# Licensed under AGPL-3.0

"""
IDSociety Science Speaks Blog RSS Generator.
Requires Selenium because the site uses React for rendering.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

import pytz
from bs4 import BeautifulSoup

from generators.base import Article, BaseFeedGenerator, stable_fallback_date
from generators.utils import (
    smart_fetch,
    fetch_html,
    parse_date,
    extract_text,
    extract_images,
    extract_article_content,
    normalize_url,
)


class IDSocietyGenerator(BaseFeedGenerator):
    """RSS generator for IDSociety Science Speaks Blog."""
    
    FEED_NAME = "idsociety"
    FEED_TITLE = "IDSociety Science Speaks Blog"
    FEED_URL = "https://www.idsociety.org/science-speaks-blog/"
    FEED_DESCRIPTION = "Latest posts from IDSA's Science Speaks blog on infectious diseases"
    FEED_LANGUAGE = "en"
    FEED_LOGO = "https://www.idsociety.org/favicon.ico"
    
    BASE_URL = "https://www.idsociety.org"
    
    # This site requires JS rendering
    REQUIRE_JS = True
    CONTENT_CHECK = "/science-speaks-blog/20"
    
    def fetch_articles(self) -> list[Article]:
        """Fetch article list from the blog homepage."""
        html = smart_fetch(
            self.FEED_URL,
            require_js=True,
            content_check=self.CONTENT_CHECK,
            selenium_wait=8,
            selenium_selector="a[href*='/science-speaks-blog/20']"
        )
        
        if not html:
            self.logger.error("Failed to fetch blog list page")
            return []
        
        return self._parse_article_list(html)
    
    def _parse_article_list(self, html: str) -> list[Article]:
        """Parse article list from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen_urls = set()
        
        # Find gridlisting-card links (the actual article cards)
        post_links = soup.select('a.gridlisting-card[href*="/science-speaks-blog/20"]')
        
        # Fallback: any link with the blog path
        if not post_links:
            post_links = soup.select('a[href*="/science-speaks-blog/20"]')
        
        self.logger.info(f"Found {len(post_links)} potential article links")
        
        for link in post_links:
            href = link.get("href", "")
            if not href:
                continue
            
            url = normalize_url(href, self.BASE_URL)
            
            if url in seen_urls:
                continue
            if url.rstrip("/").endswith("/science-speaks-blog") or "#" in url:
                continue
            
            seen_urls.add(url)
            
            title = self._extract_title(link)
            if not title or len(title) < 10:
                continue
            
            # Skip navigation/menu items
            if "View all" in title or "Guidelines" in title:
                self.logger.debug(f"Skipping nav item: {title}")
                continue
            
            date = self._extract_date(link, url)
            cover = self._extract_cover(link)
            author = self._extract_author(link)
            
            articles.append(Article(
                url=url,
                title=title,
                published_at=date,
                author=author,
                images=[cover] if cover else [],
                category="Medical",
            ))
        
        self.logger.info(f"Extracted {len(articles)} articles")
        return articles
    
    def _extract_title(self, element) -> Optional[str]:
        """Extract title from element."""
        # Prefer h4 (main article title in gridlisting-card)
        h4 = element.find("h4")
        if h4:
            title = extract_text(h4)
            if title and len(title) >= 10 and "View all" not in title:
                return title
        
        # Try img alt attribute (reliable fallback)
        img = element.find("img")
        if img and img.get("alt"):
            alt = img.get("alt", "").replace(" thumbnail", "").strip()
            if alt and len(alt) >= 10 and "View all" not in alt:
                return alt
        
        # Try other heading tags (but NOT h6 which is used for nav)
        for tag in ["h3", "h2"]:
            heading = element.find(tag)
            if heading:
                title = extract_text(heading)
                if title and "View all" not in title and len(title) >= 10:
                    return title
        
        # Try common class patterns
        for selector in [".gridlisting-card-title", ".title", ".headline"]:
            title_elem = element.select_one(selector)
            if title_elem:
                title = extract_text(title_elem)
                if title and len(title) >= 10 and "View all" not in title:
                    return title
        
        return None
    
    def _extract_date(self, element, url: str) -> Optional[datetime]:
        """Extract date from element or URL."""
        # Try to find date elements with common patterns
        date_selectors = [
            "[class*='published']", ".published", "time",
            ".date", "[class*='date']", ".meta", "[class*='meta']"
        ]
        
        for selector in date_selectors:
            date_elem = element.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # Remove common prefixes like "Published ", "Last Updated "
                date_text = re.sub(
                    r'^(Published|Last\s*Updated|Posted|Date)\s*:?\s*',
                    '', date_text, flags=re.IGNORECASE
                )
                date = parse_date(date_text)
                if date:
                    self.logger.debug(f"Found date {date} from {selector}: {date_text}")
                    return date
        
        # Try finding any text containing date pattern in the card
        text = element.get_text()
        
        # First try "Last Updated\nApril 27, 2026" pattern
        last_updated_pattern = r'Last\s*Updated[\s\n]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
        match = re.search(last_updated_pattern, text, re.IGNORECASE)
        if match:
            date = parse_date(match.group(1))
            if date:
                self.logger.debug(f"Found date from Last Updated: {date}")
                return date
        
        # Then try "April 27, 2026" style dates
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        match = re.search(date_pattern, text, re.IGNORECASE)
        if match:
            date = parse_date(match.group(0))
            if date:
                return date
        
        # Extract year from URL pattern /science-speaks-blog/YYYY/
        match = re.search(r'/science-speaks-blog/(\d{4})/', url)
        if match:
            year = int(match.group(1))
            if 2020 <= year <= 2030:
                hash_val = abs(hash(url)) % 365
                return datetime(year, 1, 1, tzinfo=pytz.UTC) + timedelta(days=hash_val)
        
        # Fallback
        return datetime.now(pytz.UTC).replace(
            day=1 + abs(hash(url)) % 28,
            month=1 + abs(hash(url)) % 12
        )
    
    def _extract_cover(self, element) -> Optional[str]:
        """Extract cover image from card element."""
        img = element.find("img")
        if img:
            src = img.get("src") or img.get("data-src")
            if src and not src.startswith("data:"):
                if src.startswith("/"):
                    src = f"{self.BASE_URL}{src}"
                return src
        return None
    
    def _extract_author(self, element) -> Optional[str]:
        """Extract author from card element."""
        author_selectors = [
            "[class*='author']", ".author", ".byline"
        ]
        for selector in author_selectors:
            author_elem = element.select_one(selector)
            if author_elem:
                text = author_elem.get_text(strip=True)
                # Remove "Authors " prefix
                text = re.sub(r'^Authors?\s*:?\s*', '', text, flags=re.IGNORECASE)
                if text and len(text) > 2:
                    return text
        return None
    
    def fetch_article_content(self, url: str) -> Optional[Article]:
        """Fetch full article content from detail page."""
        # IDSociety requires JS rendering for detail pages too
        html = smart_fetch(url, require_js=True, selenium_wait=5)
        if not html:
            self.logger.warning(f"Failed to fetch article: {url}")
            return None
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract content using common utility
        content_html, content_text = extract_article_content(soup)
        
        if not content_html:
            self.logger.warning(f"No content found for: {url}")
            return None
        
        # Create summary from text content
        summary = content_text[:500] + "..." if len(content_text) > 500 else content_text
        
        # Extract accurate publish date from detail page
        # Look for "Last Updated April 27, 2026" or similar patterns
        published_at = None
        date_selectors = [
            "[class*='updated']", "[class*='published']", ".published",
            "time", ".date", "[class*='date']", ".meta"
        ]
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # Remove common prefixes
                date_text = re.sub(
                    r'^(Last\s*Updated|Published|Posted|Date)\s*:?\s*',
                    '', date_text, flags=re.IGNORECASE
                )
                published_at = parse_date(date_text)
                if published_at:
                    self.logger.debug(f"Detail page date: {published_at} from {selector}")
                    break
        
        # Fallback: search for date pattern in page text
        if not published_at:
            text = soup.get_text()
            # First try "Last Updated\nApril 27, 2026" pattern (with possible newlines)
            last_updated_pattern = r'Last\s*Updated[\s\n]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
            match = re.search(last_updated_pattern, text, re.IGNORECASE)
            if match:
                published_at = parse_date(match.group(1))
                if published_at:
                    self.logger.debug(f"Found date from Last Updated: {published_at}")
            
            # Then try general date pattern
            if not published_at:
                date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
                match = re.search(date_pattern, text, re.IGNORECASE)
                if match:
                    published_at = parse_date(match.group(0))
        
        # Extract author from detail page
        author = None
        author_selectors = [
            "[class*='author']", ".author", ".byline", "[class*='authored']"
        ]
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author_text = author_elem.get_text(strip=True)
                author_text = re.sub(
                    r'^(Authored?\s*By|Authors?|By)\s*:?\s*',
                    '', author_text, flags=re.IGNORECASE
                )
                if author_text and len(author_text) > 2 and len(author_text) < 100:
                    author = author_text
                    break
        
        # Extract images
        images = extract_images(soup, self.BASE_URL)
        
        return Article(
            url=url,
            title="",  # Will be replaced by original title
            published_at=published_at,  # May be None, merged later
            content=content_html,  # HTML format for RSS
            summary=summary,
            author=author,
            images=images[:5],
            category="Medical",
        )


if __name__ == "__main__":
    import argparse
    import logging
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    gen = IDSocietyGenerator()
    gen.run(full_refresh=args.full, max_articles=args.max)
