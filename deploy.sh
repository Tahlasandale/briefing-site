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

# Si le dépôt n'existe pas encore localement, le cloner
if [ ! -d ".git" ]; then
    echo "🆕 Initialisation du dépôt git..."
    git init
    git remote add origin "$REPO_URL"
    git checkout -b main
    git add -A
    git commit -m "Initialisation du Briefing Quotidien"
    git push -u origin main
fi

# Déploiement via git subtree ou gh-pages
# On utilise la méthode simple: copier site/ dans un répertoire temporaire
echo "📦 Préparation du déploiement..."
TEMP_DIR=$(mktemp -d)

# Copier le contenu du site
cp -r "$SITE_DIR"/* "$TEMP_DIR/"
cp "$SITE_DIR/style.css" "$TEMP_DIR/" 2>/dev/null || true

# Aller dans le répertoire temp, initialiser git et pusher sur gh-pages
cd "$TEMP_DIR"

git init
git checkout -b "$BRANCH"
git add -A
git commit -m "Briefing du $(date +%Y-%m-%d)" --allow-empty

# Pousser
echo "☁️ Push sur GitHub ($BRANCH)..."
git push -f "$REPO_URL" "$BRANCH" 2>&1 || {
    echo "⚠️  Erreur de push. Vérifie que le repo Tahlasandale/briefing-site existe."
    echo "   Crée-le sur https://github.com/new"
    rm -rf "$TEMP_DIR"
    exit 1
}

# Nettoyage
rm -rf "$TEMP_DIR"

echo "✅ Site déployé sur GitHub Pages !"
echo "🌐 https://tahlasandale.github.io/briefing-site"

# Revenir au répertoire d'origine
cd - > /dev/null
