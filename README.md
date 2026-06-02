# Le Briefing du Matin 📰

Générateur de site statique — revue de presse quotidienne avec résumé IA, déployé sur **GitHub Pages**.

## Architecture

```
briefing-site/
├── pipeline.py          # Orchestrateur (4 étapes)
├── deploy.sh            # Déploiement GitHub Pages
├── config.yaml          # Configuration (flux RSS, IA, météo)
├── src/
│   ├── fetch.py         # Étape 1  — Récupération des flux RSS
│   ├── ai_summary.py    # Étape 2  — Résumé IA par Mistral
│   └── build.py         # Étape 3  — Construction du site statique
└── site/                # Site généré (pushé sur gh-pages)
    ├── index.html
    ├── style.css         # Thème papier vieilli
    └── archives/
        ├── index.html
        └── YYYY-MM-DD.html
```

## Pipeline

```
📡 Fetch RSS   →   🤖 AI Summary   →   🏗️ Build HTML   →   📤 Deploy
```

Exécution : `python3 pipeline.py` (ou via cron pour l'automatisation quotidienne).

## Thème

Style **papier vieilli / machine à écrire** — Special Elite + Courier Prime, palette brune, grain grainé, micro-rotations. Zéro émoji, sobre comme un journal imprimé.

## Déploiement

Le site est poussé sur la branche `gh-pages` et accessible à :
**https://tahlasandale.github.io/briefing-site/**

## Prérequis

- Python 3.10+
- Clé API Mistral (dans `.env` ou les variables d'env Hermes)
- `pip install feedparser pyyaml mistralai requests`

## Licence

MIT
