#!/bin/bash
# 📤 deploy.sh — Déploiement du site statique sur GitHub Pages
set -e

echo "📤 Déploiement du briefing..."

cd "$(dirname "$0")"
SITE_DIR="site"
REPO_URL="https://github.com/Tahlasandale/briefing-site.git"
BRANCH="gh-pages"

# Vérifier que le site a été généré
if [ ! -f "$SITE_DIR/index.html" ]; then
    echo "❌ site/index.html non trouvé. Exécute pipeline.py d'abord."
    exit 1
fi

echo "📦 Préparation du déploiement..."
TEMP_DIR=$(mktemp -d)

# Copier le contenu du site dans un dossier temporaire
cp -r "$SITE_DIR"/* "$TEMP_DIR/"
cp "$SITE_DIR/style.css" "$TEMP_DIR/" 2>/dev/null || true

# S'assurer qu'il y a un .nojekyll pour GitHub Pages
touch "$TEMP_DIR/.nojekyll"

# Initialiser git dans le dossier temporaire et pusher
cd "$TEMP_DIR"

git init -q
git checkout -b "$BRANCH" -q
git add -A
git commit -m "Briefing du $(date +%Y-%m-%d)" --allow-empty -q

echo "☁️ Push sur GitHub ($BRANCH)..."
git push -f "$REPO_URL" "$BRANCH" 2>&1

# Nettoyage
rm -rf "$TEMP_DIR"

echo "✅ Site déployé sur GitHub Pages !"
echo "🌐 https://tahlasandale.github.io/briefing-site"

cd - > /dev/null
