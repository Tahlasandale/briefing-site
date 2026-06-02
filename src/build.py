#!/usr/bin/env python3
"""
🏗️ build.py — Génération du site statique
Prend les résumés IA et construit les pages HTML.
"""

import json
import os
import shutil
import yaml
from datetime import datetime


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — {date}</title>
    <meta name="description" content="{description}">
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div class="container">
        <header class="site-header">
            <h1 class="site-title">{title}</h1>
            <p class="site-desc">{description}</p>
            <nav class="site-nav">
                <a href="/" class="nav-link">Aujourd'hui</a>
                <a href="/archives/" class="nav-link">Archives</a>
            </nav>
        </header>

        <main class="daily-briefing">
            <div class="briefing-meta">
                <time class="briefing-date" datetime="{iso_date}">{date}</time>
                <span class="article-count">{count} articles • {feeds} flux</span>
            </div>

            <div class="briefing-content">
{ai_content}
            </div>
        </main>

        <footer class="site-footer">
            <p>Généré automatiquement le {gen_date} • Briefing Quotidien</p>
            <p><a href="/archives/">Consulter les archives</a></p>
        </footer>
    </div>
</body>
</html>"""


ARCHIVE_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archives — {title}</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div class="container">
        <header class="site-header">
            <h1 class="site-title">📚 Archives</h1>
            <p class="site-desc">Tous les briefings quotidiens depuis le début</p>
            <nav class="site-nav">
                <a href="/" class="nav-link">Aujourd'hui</a>
                <a href="/archives/" class="nav-link active">Archives</a>
            </nav>
        </header>

        <main class="archives-list">
            {entries}
        </main>

        <footer class="site-footer">
            <p>Briefing Quotidien</p>
        </footer>
    </div>
</body>
</html>"""


INDEX_CARD = """            <article class="archive-card">
                <time class="archive-date" datetime="{iso_date}">{date}</time>
                <h2><a href="/{link}" class="archive-link">{title}</a></h2>
                <p class="archive-desc">{count} articles</p>
            </article>"""


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def date_fr():
    """Date en français."""
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    now = datetime.now()
    return f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"


def build_site():
    config = load_config()
    now = datetime.now()
    date_str = date_fr()
    iso_date = now.strftime("%Y-%m-%d")
    slug = iso_date  # ex: 2026-06-02

    # Charger le contenu généré par l'IA
    ai_content_path = "/tmp/briefing_ai_content.html"
    if not os.path.exists(ai_content_path):
        print("❌ Contenu IA non trouvé. Exécute ai_summary.py d'abord.")
        return False

    with open(ai_content_path) as f:
        ai_content = f.read()

    # Charger les stats RSS
    with open("/tmp/briefing_results.json") as f:
        results = json.load(f)

    total_items = sum(len(r["items"]) for r in results)
    total_feeds = len(results)

    # S'assurer que site/ existe
    os.makedirs("site", exist_ok=True)
    os.makedirs("site/archives", exist_ok=True)

    # Générer index.html (briefing du jour)
    index_html = HTML_TEMPLATE.format(
        lang=config.get("lang", "fr"),
        title=config["title"],
        description=config.get("description", ""),
        date=date_str,
        iso_date=iso_date,
        ai_content=ai_content,
        count=total_items,
        feeds=total_feeds,
        gen_date=now.strftime("%Y-%m-%d %H:%M"),
    )

    with open("site/index.html", "w") as f:
        f.write(index_html)
    print(f"✅ Page d'accueil générée: site/index.html")

    # Archiver le briefing du jour dans site/archives/YYYY-MM-DD.html
    archive_path = f"site/archives/{slug}.html"
    # Copier l'index avec un en-tête "Archives" dans le titre
    archive_html = HTML_TEMPLATE.format(
        lang=config.get("lang", "fr"),
        title=f"📜 {config['title']}",
        description=config.get("description", ""),
        date=date_str,
        iso_date=iso_date,
        ai_content=ai_content,
        count=total_items,
        feeds=total_feeds,
        gen_date=now.strftime("%Y-%m-%d %H:%M"),
    )

    with open(archive_path, "w") as f:
        f.write(archive_html)
    print(f"✅ Archive créée: site/archives/{slug}.html")

    # Re-generate la page des archives
    build_archive_page(config)

    return True


def build_archive_page(config):
    """Regénère la page d'archives avec tous les briefings passés."""
    archives_dir = "site/archives"
    entries = []

    if os.path.exists(archives_dir):
        files = sorted([f for f in os.listdir(archives_dir) if f.endswith(".html") and f != "index.html"], reverse=True)

        for fname in files:
            date_part = fname.replace(".html", "")
            try:
                dt = datetime.strptime(date_part, "%Y-%m-%d")
                jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
                mois = ["janvier", "février", "mars", "avril", "mai", "juin",
                        "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
                date_str = f"{jours[dt.weekday()]} {dt.day} {mois[dt.month-1]} {dt.year}"

                # Titre par défaut
                title = f"Briefing du {date_str}"
                entries.append(INDEX_CARD.format(
                    iso_date=date_part,
                    date=date_str,
                    link=f"archives/{fname}",
                    title=title,
                    count="Briefing quotidien",
                ))
            except ValueError:
                continue

    if not entries:
        entries = ['<p class="empty-archive">Aucun briefing pour le moment.</p>']

    archive_html = ARCHIVE_TEMPLATE.format(
        lang=config.get("lang", "fr"),
        title=config["title"],
        entries="\n".join(entries),
    )

    with open(f"{archives_dir}/index.html", "w") as f:
        f.write(archive_html)

    print(f"✅ Page d'archives mise à jour: {archives_dir}/index.html ({len(entries)} entrées)")


if __name__ == "__main__":
    build_site()
