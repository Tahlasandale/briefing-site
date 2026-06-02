#!/usr/bin/env python3
"""
📡 fetch.py — Récupération des flux RSS
Utilise feedparser en parallèle pour tous les flux configurés.
"""

import asyncio
import feedparser
import ssl
import time
from dataclasses import dataclass, field
from typing import Optional
import yaml

# Désactiver la vérification SSL pour certains flux problématiques
ssl._create_default_https_context = ssl._create_unverified_context


@dataclass
class RSSItem:
    title: str
    link: str
    summary: str
    published: str
    source: str
    category: str


@dataclass
class RSSResult:
    source: str
    category: str
    items: list[RSSItem] = field(default_factory=list)
    error: Optional[str] = None
    fetch_time: float = 0.0


def fetch_single(feed_config: dict) -> RSSResult:
    """Récupère un flux RSS unique."""
    name = feed_config["name"]
    url = feed_config["url"]
    category = feed_config.get("category", "Général")
    max_items = feed_config.get("max_items", 5)

    start = time.time()
    try:
        parsed = feedparser.parse(url)
        fetch_time = time.time() - start

        if parsed.bozo and not parsed.entries:
            return RSSResult(
                source=name,
                category=category,
                error=f"Erreur de parsing: {parsed.bozo_exception}",
                fetch_time=fetch_time,
            )

        items = []
        for entry in parsed.entries[:max_items]:
            summary = (entry.get("summary") or entry.get("description") or "")[:500]
            published = entry.get("published") or entry.get("updated") or ""
            items.append(RSSItem(
                title=entry.get("title", "Sans titre"),
                link=entry.get("link", ""),
                summary=summary,
                published=published,
                source=name,
                category=category,
            ))

        return RSSResult(
            source=name,
            category=category,
            items=items,
            fetch_time=fetch_time,
        )

    except Exception as e:
        return RSSResult(
            source=name,
            category=category,
            error=str(e),
            fetch_time=time.time() - start,
        )


def fetch_all(feeds_config: list[dict]) -> list[RSSResult]:
    """Récupère tous les flux en parallèle."""
    import concurrent.futures

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_single, feed): feed for feed in feeds_config}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Trier par catégorie
    results.sort(key=lambda r: r.category)
    return results


def main():
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    feeds = config["rss_feeds"]
    print(f"📡 Récupération de {len(feeds)} flux RSS...\n")

    results = fetch_all(feeds)

    total_items = 0
    for r in results:
        status = f"✅ {len(r.items)} articles" if not r.error else f"❌ {r.error}"
        print(f"  {r.source:25s} → {status} ({r.fetch_time:.1f}s)")
        total_items += len(r.items)

    print(f"\n📊 Total: {total_items} articles récupérés depuis {len(results)} flux")
    return results


if __name__ == "__main__":
    main()
