#!/usr/bin/env python3
"""
🚀 pipeline.py — Orchestrateur complet du Briefing Quotidien
Enchaîne : fetch RSS → résumé IA → build site → déploiement
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime


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


def main():
    start_time = time.time()
    print(f"🚀 Lancement du pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📂 Répertoire: {os.path.dirname(os.path.abspath(__file__))}")

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
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
