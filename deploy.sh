#!/bin/bash

# Opus Formosa Website Deploy Script
# This script commits all changes and pushes to GitHub Pages

echo "🚀 Deploying Opus Formosa website..."

DEPLOY_PATHS=( "." ":(exclude)internal-seatmap-admin" ":(exclude)internal-seatmap-admin/**" ":(exclude)internal-personnel-admin" ":(exclude)internal-personnel-admin/**" ":(exclude)CONTEXT.md" )

# Ensure CNAME file exists for custom domain
if [[ ! -f "CNAME" ]]; then
    echo "📄 Creating CNAME file for custom domain..."
    echo "opusformosa.org" > CNAME
    echo "✅ CNAME file created"
fi

# Update sitemap lastmod
echo "📅 Updating sitemap lastmod..."
sed -i '' "s/<lastmod>[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}<\/lastmod>/<lastmod>$(date +%Y-%m-%d)<\/lastmod>/g" sitemap.xml
echo "✅ Sitemap updated"

# Compress CSS for better performance
echo "🗜️  Compressing CSS..."
sed -e 's/^[ \t]*//' -e 's/[ \t]*$//' -e 's/[ \t]*\([{};:,]\)/\1/g' -e '/^$/d' style.css > style.min.css
mv style.min.css style.css
echo "✅ CSS compressed"

# Check if there are any changes to commit
if [[ -n $(git status --porcelain -- "${DEPLOY_PATHS[@]}") ]]; then
    echo "📝 Committing changes..."
    git add -A -- "${DEPLOY_PATHS[@]}"
    git commit -m "Update website - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "✅ Changes committed"
else
    echo "ℹ️  No changes to commit"
fi

echo "⬆️  Pushing to GitHub..."
git push origin master

echo "🎉 Deployment complete!"
echo "🌐 Website will be updated at: https://opusformosa.org"
echo "   (DNS propagation may take 24-48 hours for first setup)"
