#!/usr/bin/env python3
"""
🚀 pipeline.py — Orchestrateur complet du Briefing Quotidien
Enchaîne : fetch RSS → résumé IA → build site → déploiement
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ─── Historique cross-day (évite les répétitions d'articles) ──────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(PROJECT_DIR, "data", "history.json")
HISTORY_MAX_DAYS = 7  # nettoyage automatique après 7 jours


def load_history() -> dict[str, float]:
    """Charge l'historique des articles déjà publiés.
    Retourne un dict {url_ou_titre: timestamp_unix}."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_history(history: dict[str, float]) -> None:
    """Sauvegarde l'historique et nettoie les entrées de plus de HISTORY_MAX_DAYS."""
    cutoff = time.time() - (HISTORY_MAX_DAYS * 86400)
    cleaned = {k: v for k, v in history.items() if v >= cutoff}
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(cleaned, f, indent=2)
    purged = len(history) - len(cleaned)
    if purged:
        print(f"🧹 {purged} entrées d'historique nettoyées (> {HISTORY_MAX_DAYS} jours)")


def filter_history(results_dict: list[dict], history: dict[str, float]) -> tuple[list[dict], int]:
    """Filtre les articles déjà présents dans l'historique.
    Retourne (results_dict filtré, nombre d'articles filtrés)."""
    filtered_total = 0
    for r in results_dict:
        before = len(r["items"])
        r["items"] = [
            item for item in r["items"]
            if item.get("link") not in history and item.get("title") not in history
        ]
        after = len(r["items"])
        filtered_total += before - after
    return results_dict, filtered_total


def update_history(results_dict: list[dict], history: dict[str, float]) -> None:
    """Ajoute les articles du jour à l'historique."""
    now = time.time()
    for r in results_dict:
        for item in r["items"]:
            key = item.get("link") or item.get("title")
            if key:
                history[key] = now
    save_history(history)


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run_script(script_name):
    """Exécute un script Python du dossier src/."""
    script_path = os.path.join("src", script_name)
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
    )
    print(result.stdout)
    if result.stderr:
        print(f"⚠️  Stderr: {result.stderr}")
    return result.returncode == 0


# ─── Notification Telegram ────────────────────────────────────────────


def send_telegram_notification(url: str) -> bool:
    """Envoie un message Telegram avec l'URL de la gazette du jour."""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID2")

    # Fallback vers le .env
    if not token or not chat_id:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        v = v.strip().strip('"')
                        if k == "TELEGRAM_TOKEN":
                            token = v
                        elif k == "CHAT_ID2":
                            chat_id = v

    if not token or not chat_id:
        print("⚠️  TELEGRAM_TOKEN ou CHAT_ID2 manquant — notification ignorée")
        return False

    today = datetime.now().strftime("%A %d %B %Y")
    # Nettoyer le token des guillemets résiduels
    token = token.strip().strip('"\'')
    chat_id = chat_id.strip().strip('"\'')

    message = (
        f"📰 *Le Briefing du Matin — {today}*\n\n"
        f"Votre gazette quotidienne est prête !\n"
        f"🌐 {url}"
    )

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            print(f"✅ Notification Telegram envoyée → {chat_id}")
            return True
        else:
            print(f"⚠️  Erreur Telegram: {result.get('description', 'inconnue')}")
            return False
    except urllib.error.HTTPError as e:
        print(f"⚠️  Erreur HTTP Telegram: {e.code} — {e.read().decode()}")
        return False
    except Exception as e:
        print(f"⚠️  Erreur réseau Telegram: {e}")
        return False


# ─── Pipeline principal ────────────────────────────────────────────────


def main():
    start_time = time.time()
    print(f"🚀 Lancement du pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📂 Répertoire: {os.path.dirname(os.path.abspath(__file__))}")

    # Charger l'historique cross-day
    history = load_history()
    print(f"📚 Historique chargé: {len(history)} articles déjà publiés")

    # Charger la config
    import yaml
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    # Étape 1: Fetch RSS
    step("📡 ÉTAPE 1/4 — Récupération des flux RSS")
    from src.fetch import fetch_all
    results = fetch_all(config["rss_feeds"])

    # Sauvegarder les résultats pour les autres étapes
    results_dict = []
    for r in results:
        results_dict.append({
            "source": r.source,
            "category": r.category,
            "error": r.error,
            "fetch_time": r.fetch_time,
            "items": [
                {"title": i.title, "link": i.link, "summary": i.summary,
                 "published": i.published, "source": i.source, "category": i.category}
                for i in r.items
            ],
        })

    with open("/tmp/briefing_results.json", "w") as f:
        json.dump(results_dict, f, ensure_ascii=False, indent=2)

    total_items = sum(len(r["items"]) for r in results_dict)
    print(f"✅ {total_items} articles récupérés depuis {len(results_dict)} flux")

    # Filtrer les articles déjà publiés les jours précédents
    if history:
        results_dict, filtered_count = filter_history(results_dict, history)
        if filtered_count > 0:
            total_items = sum(len(r["items"]) for r in results_dict)
            print(f"🔄 {filtered_count} article(s) déjà publié(s) retiré(s) — {total_items} restants")

    # Vérifier qu'on a des articles
    if total_items == 0:
        print("❌ Aucun article récupéré. Abandon.")
        return False

    # Étape 2: Résumé IA
    step(f"🤖 ÉTAPE 2/4 — Génération du résumé IA ({config['ai']['model']})")

    # Charger la clé API (priorité au fichier .env)
    api_key = None
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    if k == "MISTRAL_API_KEY":
                        api_key = v.strip()
                        break
    if not api_key:
        api_key = os.environ.get("MISTRAL_API_KEY")

    if not api_key:
        print("❌ MISTRAL_API_KEY non trouvée dans .env ou MISTRAL_API_KEY")
        print("   Ajoute-la dans le fichier .env : MISTRAL_API_KEY=votre_clé")
        return False

    from src.ai_summary import build_prompt, call_mistral
    date_str = datetime.now().strftime("%A %d %B %Y")
    prompt = build_prompt(results_dict, date_str=date_str)
    ai_content = call_mistral(prompt, api_key, config["ai"]["model"])

    with open("/tmp/briefing_ai_content.html", "w") as f:
        f.write(ai_content)

    print(f"✅ Résumé généré ({len(ai_content)} caractères)")

    # Étape 3: Build site
    step("🏗️ ÉTAPE 3/4 — Construction du site statique")
    from src.build import build_site
    success = build_site()

    if not success:
        print("❌ Échec de la construction du site")
        return False

    # Étape 4: Déploiement
    step("📤 ÉTAPE 4/4 — Déploiement sur GitHub Pages")

    # Le déploiement se fait via deploy.sh
    result = subprocess.run(
        ["bash", "deploy.sh"],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
    )
    print(result.stdout)
    if result.stderr:
        print(f"⚠️  {result.stderr}")

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  ✅ PIPELINE TERMINÉ en {elapsed:.1f}s")
    print(f"{'='*60}")

    # Mettre à jour l'historique cross-day
    update_history(results_dict, history)
    print(f"📚 Historique mis à jour: {len(history)} entrées")

    # Envoyer la notification Telegram avec le lien du jour
    today_slug = datetime.now().strftime("%Y-%m-%d")
    gazette_url = f"https://tahlasandale.github.io/briefing-site/archives/{today_slug}.html"
    send_telegram_notification(gazette_url)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
