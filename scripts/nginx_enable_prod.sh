#!/usr/bin/env bash
# scripts/nginx_enable_prod.sh <project-name>
set -euo pipefail
NAME="${1:-my-news}"
SERVER_NAME="${SERVER_NAME:-news.example.com}"
FRONT_ROOT="${FRONT_ROOT:-/srv/apps/${NAME}/frontend_dist}"
API_UPSTREAM="${API_UPSTREAM:-127.0.0.1:8000}"

REPO_DIR="$(pwd)"
TPL="${REPO_DIR}/deploy/nginx/site.prod.conf.tpl"
OUT="${REPO_DIR}/deploy/nginx/${NAME}.conf"
ENABLED="/etc/nginx/sites-enabled/${NAME}.conf"

sudo mkdir -p "$(dirname "$OUT")"
sed -e "s/{{SERVER_NAME}}/${SERVER_NAME}/g" \
    -e "s,{{FRONT_ROOT}},${FRONT_ROOT},g" \
    -e "s,{{API_UPSTREAM}},${API_UPSTREAM},g" \
    "$TPL" | sudo tee "$OUT" >/dev/null

sudo ln -sfn "$OUT" "$ENABLED"
sudo nginx -t
sudo systemctl reload nginx
echo "✔ enabled $ENABLED -> $OUT"
echo "   SERVER_NAME=$SERVER_NAME FRONT_ROOT=$FRONT_ROOT API_UPSTREAM=$API_UPSTREAM"
