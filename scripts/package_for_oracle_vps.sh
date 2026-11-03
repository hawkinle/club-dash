#!/usr/bin/env bash
# ==============================================================================
# Upper Horton Sports Club — Package Bundle for Oracle Cloud Always Free VPS
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."
BUNDLE_PATH="/home/leith/AI/Square/uhsc_oracle_deploy.tar.gz"

echo "📦 Packaging Upper Horton Sports Club Executive Suite (including 55k+ order DuckDB ledger)..."
tar --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='src/__pycache__' \
    --exclude='*.pyc' \
    --exclude='uhsc_oracle_deploy.tar.gz' \
    -czf "$BUNDLE_PATH" \
    app.py Dockerfile docker-compose.yml requirements.txt README.md \
    .env .env.example .gitignore .dockerignore \
    src/ scripts/ data/club_sales.duckdb

chmod 600 "$BUNDLE_PATH"
SIZE_MB=$(du -h "$BUNDLE_PATH" | cut -f1)
echo "✅ Created secure deployment bundle: $BUNDLE_PATH ($SIZE_MB)"
echo ""
echo "🚀 Next step — copy to your Oracle Free VPS:"
echo "   scp -i <your-oracle-ssh-key.key> $BUNDLE_PATH ubuntu@<YOUR_ORACLE_VPS_IP>:~/"
