#!/usr/bin/env sh
# Action Platform in one command, Dokploy-style:
#
#   curl -fsSL https://get.actionplatform.dev | sh
#   curl -fsSL https://get.actionplatform.dev | sh -s -- platform.example.com you@example.com   # with TLS
#
# Installs Docker if missing, writes /opt/action-platform/.env with fresh
# secrets, starts Postgres + API + web (+ Traefik when a domain is given)
# and prints the URL. Everything else happens in the browser.
set -eu

DOMAIN="${1:-}"
EMAIL="${2:-}"
DIR="${AP_DIR:-/opt/action-platform}"
REF="${AP_REF:-master}"
RAW="https://raw.githubusercontent.com/actionplatform/action-platform/$REF/deploy"

say() { printf '\033[1m→ %s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo sh install.sh)" >&2; exit 1; }
if [ -n "$DOMAIN" ] && [ -z "$EMAIL" ]; then echo "usage: install.sh [domain acme-email]" >&2; exit 1; fi

if ! command -v docker >/dev/null 2>&1; then
  say "installing Docker"
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || { echo "docker compose plugin missing" >&2; exit 1; }

mkdir -p "$DIR"; cd "$DIR"
say "fetching compose files ($REF)"
curl -fsSL "$RAW/docker-compose.yml" -o docker-compose.yml
curl -fsSL "$RAW/.env.example" -o .env.example

if [ -f .env ]; then
  say "keeping existing .env"
else
  IP="$(curl -fs4 https://api.ipify.org 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo 127.0.0.1)"
  if [ -n "$DOMAIN" ]; then URL="https://$DOMAIN"; else URL="http://$IP:3000"; fi
  cp .env.example .env
  sed -i "s|^PUBLIC_URL=.*|PUBLIC_URL=$URL|; s|^DOMAIN=.*|DOMAIN=$DOMAIN|; s|^ACME_EMAIL=.*|ACME_EMAIL=$EMAIL|" .env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env
  sed -i "s|^BETTER_AUTH_SECRET=.*|BETTER_AUTH_SECRET=$(openssl rand -hex 32)|" .env
  chmod 600 .env
fi

say "starting"
if [ -n "$DOMAIN" ]; then
  docker compose --profile tls pull
  docker compose --profile tls up -d
else
  docker compose pull
  docker compose up -d
fi

URL="$(sed -n 's/^PUBLIC_URL=//p' .env)"
echo
say "Action Platform is up: $URL"
echo "  Open it, create the first account and organization — that's the whole setup."
echo "  Files: $DIR   (.env holds the secrets; docker compose logs -f to watch)"
