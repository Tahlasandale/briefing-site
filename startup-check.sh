#!/bin/bash
# 🚀 startup-check.sh — Vérifie au démarrage si le briefing du jour a été fait
# Si pas encore fait, exécute le pipeline

set -e

cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
TODAY=$(date +%Y-%m-%d)
DATE_FILE="/tmp/briefing_last_run"

echo "🔍 Vérification démarrage — Briefing du $TODAY"

# Vérifier si le pipeline a déjà tourné aujourd'hui
if [ -f "$DATE_FILE" ]; then
    LAST_RUN=$(cat "$DATE_FILE")
    if [ "$LAST_RUN" = "$TODAY" ]; then
        echo "✅ Briefing déjà effectué aujourd'hui ($TODAY). Rien à faire."
        exit 0
    fi
fi

# Vérifier l'heure actuelle — ne pas lancer avant 6h du matin
HOUR=$(date +%H)
if [ "$HOUR" -lt 6 ]; then
    echo "⏰ Il n'est que $(date +%H:%M), avant 6h. Le cron du matin s'en chargera."
    exit 0
fi

echo "⚡ Démarrage détecté après 6h et briefing pas encore fait → Lancement du pipeline !"
cd "$PROJECT_DIR"

# Activer le venv si présent
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Lancer le pipeline
python3 pipeline.py

# Marquer la date d'exécution
echo "$TODAY" > "$DATE_FILE"

echo "✅ Startup-check terminé."
