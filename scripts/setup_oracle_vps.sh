#!/usr/bin/env bash
# ==============================================================================
# Upper Horton Sports Club — 1-Command Oracle Free VPS Setup & Launch Script
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🏉 Setting up Upper Horton Sports Club Executive Suite on Oracle VPS..."

# 1. Set Host Timezone to NSW Local Time (Australia/Sydney)
if command -v timedatectl >/dev/null 2>&1; then
    echo "🕒 Setting VPS timezone to Australia/Sydney..."
    sudo timedatectl set-timezone Australia/Sydney || true
fi

# 1b. Auto-Provision 4GB Swap File (Essential for VM.Standard.E2.1.Micro 1GB RAM instances)
if [ ! -f /swapfile ] && [ "$(free -m | awk '/^Swap:/ {print $2}')" -lt 2048 ]; then
    echo "💾 Provisioning 4GB swapfile for smooth Docker & DuckDB performance..."
    sudo fallocate -l 4G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
    fi
fi

# 2. Install Docker & Docker Compose Plugin if not already installed
if ! command -v docker >/dev/null 2>&1; then
    echo "🐳 Installing Docker Engine & Docker Compose..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
fi

# 3. Check for CLOUDFLARE_TUNNEL_TOKEN in .env
if ! grep -q "^CLOUDFLARE_TUNNEL_TOKEN=ey" .env 2>/dev/null; then
    echo ""
    echo "🔑 Cloudflare Tunnel Setup:"
    read -r -p "Paste your Cloudflare Tunnel Token (starts with eyJ...): " CF_TOKEN
    if [ -n "$CF_TOKEN" ]; then
        grep -v "^CLOUDFLARE_TUNNEL_TOKEN=" .env > .env.tmp || true
        mv .env.tmp .env
        echo "CLOUDFLARE_TUNNEL_TOKEN=${CF_TOKEN}" >> .env
    fi
fi

# 4. Enforce Strict Ownership (UID 1000 = appuser inside container) & Permissions (chmod 600)
echo "🔒 Locking down file permissions (.env & DuckDB ledger)..."
sudo chown -R 1000:1000 data/
sudo chmod 700 data/
sudo chmod 600 data/club_sales.duckdb .env

# 5. Build and Start the 3-Container Stack (Streamlit + 02:00 AM Nightly Sync + Cloudflared)
echo "🚀 Building and launching containers..."
sudo docker compose up -d --build

echo ""
echo "✅ Upper Horton Sports Club Executive Suite is LIVE!"
sudo docker compose ps
