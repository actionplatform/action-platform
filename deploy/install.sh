#!/usr/bin/env sh
set -eu

DOMAIN="${1:-}"
EMAIL="${2:-}"
DIR="${AP_DIR:-/opt/action-platform}"
REPO="actionplatform/action-platform"

say() { printf '\033[1m→ %s\033[0m\n' "$*"; }
die() { echo "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run as root (sudo sh install.sh)"
if [ -n "$DOMAIN" ] && [ -z "$EMAIL" ]; then die "usage: install.sh [domain acme-email]"; fi
if [ -n "$DOMAIN" ] && ! printf '%s' "$DOMAIN" | grep -Eq '^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$'; then die "domain: letters, digits, dots and hyphens only"; fi
if [ -n "$EMAIL" ] && ! printf '%s' "$EMAIL" | grep -Eq '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'; then die "acme-email does not look like an address"; fi

if [ -n "${AP_REF:-}" ]; then
  REF="$AP_REF"
  printf '%s' "$REF" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || die "AP_REF must be a release tag (vX.Y.Z), not a branch"
else
  say "resolving the latest release"
  REF="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" | sed -n 's/^ *"tag_name": *"\(v[0-9][0-9.]*\)".*/\1/p' | head -1)"
  [ -n "$REF" ] || die "could not resolve the latest release; set AP_REF=vX.Y.Z"
fi
RAW="https://raw.githubusercontent.com/$REPO/$REF/deploy"

if ! command -v docker >/dev/null 2>&1; then
  say "installing Docker (get.docker.com, over TLS)"
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh
fi
docker compose version >/dev/null 2>&1 || die "docker compose plugin missing"

mkdir -p "$DIR"; cd "$DIR"
say "fetching compose files ($REF)"
curl -fsSL "$RAW/docker-compose.yml" -o docker-compose.yml
curl -fsSL "$RAW/.env.example" -o .env.example

set_env() {
  key="$1"; value="$2"
  awk -v k="$key" -v v="$value" 'BEGIN { done = 0 } index($0, k "=") == 1 { print k "=" v; done = 1; next } { print } END { if (!done) print k "=" v }' .env > .env.tmp
  mv .env.tmp .env
}

if [ -f .env ]; then
  say "keeping existing .env"
else
  umask 077
  cp .env.example .env
  if [ -n "$DOMAIN" ]; then
    URL="https://$DOMAIN"
  else
    IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    [ -n "$IP" ] || IP="$(curl -fs4 https://api.ipify.org 2>/dev/null | grep -E '^[0-9.]+$' || echo 127.0.0.1)"
    URL="http://$IP:3000"
  fi
  set_env PUBLIC_URL "$URL"
  set_env DOMAIN "$DOMAIN"
  set_env ACME_EMAIL "$EMAIL"
  set_env POSTGRES_PASSWORD "$(openssl rand -hex 24)"
  set_env BETTER_AUTH_SECRET "$(openssl rand -hex 32)"
  set_env AP_API_TOKEN "$(openssl rand -hex 32)"
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
