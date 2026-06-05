#!/usr/bin/env python3
"""
📡 fetch.py — Récupération des flux RSS
Utilise feedparser en parallèle pour tous les flux configurés.
"""

import asyncio
import calendar
import feedparser
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


def _entry_within_24h(entry) -> bool:
    """Vérifie si un article RSS a moins de 24h et n'est pas dans le futur."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return True  # pas de date → on garde (le dédoublonnage gérera les répétitions)
    published_ts = calendar.timegm(parsed)
    age = time.time() - published_ts
    return 0 <= age <= 172800  # entre 0 et 48h, rejette les dates futures


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
        # Filtrer les articles de moins de 24h, garder les max_items plus récents
        fresh_entries = [e for e in parsed.entries if _entry_within_24h(e)]
        filtered = len(parsed.entries) - len(fresh_entries)
        if filtered:
            print(f"  ⏳ {name}: {filtered} articles filtrés (>48h), {len(fresh_entries)} gardés")
        for entry in fresh_entries[:max_items]:
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
    """Récupère tous les flux en parallèle, avec dédoublonnage intra-run."""
    import concurrent.futures

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_single, feed): feed for feed in feeds_config}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Dédoublonnage intra-run : un même article peut venir de plusieurs flux
    seen_urls: set[str] = set()
    for r in results:
        deduped = []
        for item in r.items:
            key = item.link or item.title
            if key not in seen_urls:
                seen_urls.add(key)
                deduped.append(item)
        if len(deduped) < len(r.items):
            print(f"  🔄 {r.source}: {len(r.items) - len(deduped)} doublon(s) retiré(s)")
        r.items = deduped

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
