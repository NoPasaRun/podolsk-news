#!/usr/bin/env bash
# scripts/nginx_disable_prod.sh <project-name>
set -euo pipefail
NAME="${1}"
ENABLED="/etc/nginx/sites-enabled/${NAME}.conf"
if [[ -e "$ENABLED" || -L "$ENABLED" ]]; then
  sudo rm -f "$ENABLED"
  sudo nginx -t
  sudo systemctl reload nginx
  echo "✔ disabled $ENABLED"
else
  echo "nothing to disable: $ENABLED not found"
fi
