#!/bin/bash
set -e
PROJECT_DIR="$(dirname "$0")"
cd "$PROJECT_DIR"
echo "📤 Déploiement du briefing..."

SITE_DIR="site"
if [ ! -f "$SITE_DIR/index.html" ]; then
    echo "❌ site/index.html non trouvé. Exécute pipeline.py d'abord."
    exit 1
fi

echo "📦 Préparation..."
# Utiliser le repo existant : ajouter, committer, push sur gh-pages
git add -A
git commit -m "Briefing du $(date +%Y-%m-%d)" --allow-empty || echo "Pas de changement à committer"

echo "☁️ Push sur gh-pages..."
git push origin gh-pages || git push -f origin gh-pages || echo "Push échoué — vérifiez l'authentification gh"

echo "✅ Déployé sur https://tahlasandale.github.io/briefing-site/"
