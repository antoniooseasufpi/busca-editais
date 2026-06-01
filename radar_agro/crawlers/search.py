from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Callable, Iterable
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

from radar_agro.config.settings import (
    CATEGORIES,
    MAX_RESULTS_PER_QUERY,
    RATE_LIMIT_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    RSS_FEEDS,
    USER_AGENT,
)


@dataclass
class RawOpportunity:
    title: str
    url: str
    snippet: str
    source: str
    category_hint: str
    query: str
    collected_at: str
    published_at: str | None = None

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.strip().lower().encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["id"] = self.id
        return data


class AgroOpportunityCrawler:
    """Coleta oportunidades com dependencias simples e sem infraestrutura externa obrigatoria."""

    def __init__(self, progress_callback: Callable[[dict], None] | None = None) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.progress_callback = progress_callback

    def run(self) -> list[dict]:
        results: list[RawOpportunity] = []
        total_queries = sum(len(queries) for queries in CATEGORIES.values())
        query_index = 0
        for category, queries in CATEGORIES.items():
            for query in queries:
                query_index += 1
                self._emit(
                    {
                        "stage": "coleta",
                        "message": f"Buscando {query_index}/{total_queries}: {query}",
                        "current": query_index,
                        "total": total_queries,
                        "stage_percent": self._percent(query_index - 1, total_queries),
                        "overall_percent": int(self._percent(query_index - 1, total_queries) * 0.35),
                        "found_count": len(results),
                    }
                )
                google_results = self._search_google_news_rss(query, category)
                results.extend(google_results)
                self._emit(
                    {
                        "stage": "coleta",
                        "message": f"Google News RSS retornou {len(google_results)} resultado(s) para: {query}",
                        "current": query_index,
                        "total": total_queries,
                        "stage_percent": self._percent(query_index, total_queries),
                        "overall_percent": int(self._percent(query_index, total_queries) * 0.35),
                        "found_count": len(results),
                    }
                )
                duck_results = self._search_duckduckgo(query, category)
                results.extend(duck_results)
                self._emit(
                    {
                        "stage": "coleta",
                        "message": f"DuckDuckGo retornou {len(duck_results)} resultado(s) para: {query}",
                        "current": query_index,
                        "total": total_queries,
                        "stage_percent": self._percent(query_index, total_queries),
                        "overall_percent": int(self._percent(query_index, total_queries) * 0.35),
                        "found_count": len(results),
                    }
                )
                time.sleep(RATE_LIMIT_SECONDS)

        self._emit(
            {
                "stage": "coleta",
                "message": "Lendo feeds institucionais",
                "current": total_queries,
                "total": total_queries,
                "stage_percent": 95,
                "overall_percent": 33,
                "found_count": len(results),
            }
        )
        results.extend(self._read_institutional_feeds())
        unique = [item.to_dict() for item in self._deduplicate(results)]
        self._emit(
            {
                "stage": "coleta",
                "message": f"Coleta finalizada: {len(unique)} resultado(s) únicos",
                "current": total_queries,
                "total": total_queries,
                "stage_percent": 100,
                "overall_percent": 35,
                "found_count": len(unique),
            }
        )
        return unique

    def _search_google_news_rss(self, query: str, category: str) -> list[RawOpportunity]:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        )
        feed = self._parse_feed(url)
        return [
            RawOpportunity(
                title=entry.get("title", "").strip(),
                url=entry.get("link", "").strip(),
                snippet=self._clean_html(entry.get("summary", "")),
                source=self._entry_source(entry, "Google News RSS"),
                category_hint=category,
                query=query,
                collected_at=datetime.now().isoformat(timespec="seconds"),
                published_at=self._entry_date(entry),
            )
            for entry in feed.entries[:MAX_RESULTS_PER_QUERY]
            if entry.get("title") and entry.get("link")
        ]

    def _search_duckduckgo(self, query: str, category: str) -> list[RawOpportunity]:
        try:
            response = self.session.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        results: list[RawOpportunity] = []
        for item in soup.select(".result")[:MAX_RESULTS_PER_QUERY]:
            title_node = item.select_one(".result__title a")
            snippet_node = item.select_one(".result__snippet")
            if not title_node:
                continue
            title = title_node.get_text(" ", strip=True)
            url = title_node.get("href", "").strip()
            if not title or not url:
                continue
            results.append(
                RawOpportunity(
                    title=title,
                    url=url,
                    snippet=snippet_node.get_text(" ", strip=True) if snippet_node else "",
                    source="DuckDuckGo HTML",
                    category_hint=category,
                    query=query,
                    collected_at=datetime.now().isoformat(timespec="seconds"),
                )
            )
        return results

    def _read_institutional_feeds(self) -> list[RawOpportunity]:
        results: list[RawOpportunity] = []
        for feed_url in RSS_FEEDS:
            feed = self._parse_feed(feed_url)
            for entry in feed.entries[:MAX_RESULTS_PER_QUERY]:
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                matched_category = self._match_category(text)
                if not matched_category:
                    continue
                results.append(
                    RawOpportunity(
                        title=entry.get("title", "").strip(),
                        url=entry.get("link", feed_url).strip(),
                        snippet=self._clean_html(entry.get("summary", "")),
                        source=feed.feed.get("title", feed_url),
                        category_hint=matched_category,
                        query="rss institucional",
                        collected_at=datetime.now().isoformat(timespec="seconds"),
                        published_at=self._entry_date(entry),
                    )
                )
        return results

    def _parse_feed(self, url: str) -> feedparser.FeedParserDict:
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException:
            return feedparser.parse("")
        return feedparser.parse(response.text)

    def _emit(self, event: dict) -> None:
        if self.progress_callback:
            self.progress_callback(event)

    @staticmethod
    def _percent(current: int, total: int) -> int:
        if total <= 0:
            return 100
        return min(100, max(0, int(round((current / total) * 100))))

    def _match_category(self, text: str) -> str | None:
        for category, queries in CATEGORIES.items():
            if any(term.lower() in text for query in queries for term in query.split()):
                return category
        return None

    @staticmethod
    def _clean_html(value: str) -> str:
        return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)

    @staticmethod
    def _entry_source(entry: feedparser.FeedParserDict, fallback: str) -> str:
        source = entry.get("source")
        if isinstance(source, dict) and source.get("title"):
            return str(source["title"])
        return fallback

    @staticmethod
    def _entry_date(entry: feedparser.FeedParserDict) -> str | None:
        date_value = entry.get("published") or entry.get("updated")
        if not date_value:
            return None
        try:
            parsed = parsedate_to_datetime(date_value)
        except (TypeError, ValueError):
            return None
        return parsed.date().isoformat()

    @staticmethod
    def _deduplicate(items: Iterable[RawOpportunity]) -> list[RawOpportunity]:
        seen: set[str] = set()
        unique: list[RawOpportunity] = []
        for item in items:
            if item.id in seen:
                continue
            seen.add(item.id)
            unique.append(item)
        return unique
