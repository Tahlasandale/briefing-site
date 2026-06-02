#!/usr/bin/env python3
"""
🤖 ai_summary.py — Résumé IA des actualités via Mistral API
"""

import json
import os
import requests
import yaml
from datetime import datetime

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


def build_prompt(results, weather_data=None, date_str=None):
    """Construit le prompt pour l'IA."""
    if date_str is None:
        date_str = datetime.now().strftime("%d %B %Y")

    # Grouper par catégorie
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        for item in r["items"]:
            categories[cat].append(item)

    date_fr = datetime.now().strftime("%A %d %B %Y")

    prompt = f"""Tu es un rédacteur de briefing matinal. Génère un résumé structuré et agréable à lire des actualités du {date_fr}.

Format de réponse: Tu réponds UNIQUEMENT avec le contenu HTML du briefing, sans balises ```html ni aucun wrapper. Le contenu sera inséré directement dans une page.

Le HTML doit contenir:
- Un sous-titre avec la date
- Un paragraphe d'introduction (2-3 phrases) qui donne le ton de la journée
- Pour chaque catégorie, une section avec un titre et les articles
- Chaque article doit avoir son titre en lien cliquable, et un résumé court (1-2 phrases max)
- Un ton chaleureux, optimiste mais professionnel
- Style: utilise des classes CSS existantes (pas de style inline)
- Structure propre avec des balises sémantiques

Categories et articles du jour:
"""

    for cat, items in categories.items():
        prompt += f"\n## {cat}\n"
        for item in items:
            prompt += f"- [{item['title']}]({item['link']})\n"
            if item.get('summary'):
                # Nettoyer le résumé
                summary = item['summary'].replace('\n', ' ').strip()[:300]
                prompt += f"  Résumé: {summary}\n"

    prompt += """
\nImportant: 
- Rédige UNIQUEMENT le HTML, pas de markdown ni de code blocks autour
- Utilise des classes comme .category-title, .article-card, .article-title, .article-summary
- Sois concis mais pertinent
- Si une section est vide, ne l'inclus pas
- Ajoute une section "✨ En Bref" à la fin avec les 3 actualités les plus importantes de la journée"""

    return prompt


def call_mistral(prompt, api_key, model="mistral-small-latest"):
    """Appelle l'API Mistral."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Tu es un assistant spécialisé dans la rédaction de briefings matinaux en français. Tu génères uniquement du HTML propre et sémantique.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    response = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    # Nettoyer les possibles balises de code
    content = content.strip()
    if content.startswith("```html"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def main():
    # Charger config
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    api_key = None
    # Priorité au fichier .env
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    if k == "MISTRAL_API_KEY":
                        api_key = v
                        break
    if not api_key:
        api_key = os.environ.get("MISTRAL_API_KEY")

    if not api_key:
        print("❌ MISTRAL_API_KEY non trouvée")
        return None

    # Charger les résultats RSS depuis un fichier temporaire
    import json
    with open("/tmp/briefing_results.json") as f:
        results = json.load(f)

    model = config["ai"]["model"]
    print(f"🤖 Génération du briefing avec Mistral ({model})...")

    prompt = build_prompt(results)
    html_content = call_mistral(prompt, api_key, model)

    with open("/tmp/briefing_ai_content.html", "w") as f:
        f.write(html_content)

    print(f"✅ Résumé IA généré ({len(html_content)} caractères)")
    return html_content


if __name__ == "__main__":
    main()
