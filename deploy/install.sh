#!/usr/bin/env sh
set -eu

REPO="actionplatform/action-platform"
IMAGES="${AP_IMAGE_PREFIX:-actionplatformio/action-platform}"

say() { printf '\033[1m→ %s\033[0m\n' "$*"; }
die() { echo "$*" >&2; exit 1; }

latest_stable() {
  tr ',{}[]' '\n\n\n\n\n' \
    | sed -n "s/^[[:space:]]*\"tag_name\":[[:space:]]*\"$1\/v\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\)\".*/\1/p" \
    | sort -t. -k1,1n -k2,2n -k3,3n \
    | tail -n 1
}

pinned_version() {
  printf '%s' "$2" | grep -Eq "^$1/v[0-9]+\.[0-9]+\.[0-9]+$" || die "$3 must be a release tag ($1/vX.Y.Z)"
  printf '%s' "${2#"$1"/v}"
}

image_version() {
  [ -f .env ] || return 0
  sed -n "s/^$1=.*:\([^:/]*\)$/\1/p" .env | tail -n 1
}

set_env() {
  key="$1"; value="$2"
  awk -v k="$key" -v v="$value" 'BEGIN { done = 0 } index($0, k "=") == 1 { print k "=" v; done = 1; next } { print } END { if (!done) print k "=" v }' .env > .env.tmp
  mv .env.tmp .env
}

compose() {
  if [ -n "$(sed -n 's/^DOMAIN=\(..*\)$/\1/p' .env 2>/dev/null)" ]; then
    docker compose --profile tls "$@"
  else
    docker compose "$@"
  fi
}

resolve_versions() {
  API_VERSION=""; WEB_VERSION=""
  [ -z "${AP_REF:-}" ] || API_VERSION="$(pinned_version api "$AP_REF" AP_REF)"
  [ -z "${AP_WEB_REF:-}" ] || WEB_VERSION="$(pinned_version web "$AP_WEB_REF" AP_WEB_REF)"
  if [ -z "$API_VERSION" ] || [ -z "$WEB_VERSION" ]; then
    say "resolving the latest api and web releases"
    releases="$(curl -fsSL "https://api.github.com/repos/$REPO/releases?per_page=100")" || die "could not list the releases; set AP_REF=api/vX.Y.Z and AP_WEB_REF=web/vX.Y.Z"
    [ -n "$API_VERSION" ] || API_VERSION="$(printf '%s' "$releases" | latest_stable api)"
    [ -n "$WEB_VERSION" ] || WEB_VERSION="$(printf '%s' "$releases" | latest_stable web)"
  fi
  [ -n "$API_VERSION" ] || die "could not resolve the latest api release; set AP_REF=api/vX.Y.Z"
  [ -n "$WEB_VERSION" ] || die "could not resolve the latest web release; set AP_WEB_REF=web/vX.Y.Z"
}

backup_database() {
  mkdir -p backups
  chmod 700 backups
  file="backups/pre-upgrade-$(date -u +%Y%m%dT%H%M%SZ).sql"
  compose up -d --wait postgres
  compose exec -T postgres pg_dump -U action_platform action_platform > "$file" || { rm -f "$file"; die "pg_dump failed; nothing was changed"; }
  say "database saved to $DIR/$file"
}

setup_hint() {
  if compose up -d --wait api >/dev/null 2>&1 && TOKEN="$(compose exec -T api action-platform-api setup token 2>/dev/null)" && [ -n "$TOKEN" ]; then
    echo "  Open it and create the first account and organization; the first account asks for this setup token:"
    echo
    echo "      $TOKEN"
    echo
    echo "  (print it again with: cd $DIR && docker compose exec api action-platform-api setup token)"
  else
    echo "  Open it and sign in. A new instance asks for the setup token: cd $DIR && docker compose exec api action-platform-api setup token"
  fi
}

main() {
  DOMAIN="${1:-}"
  EMAIL="${2:-}"
  DIR="${AP_DIR:-/opt/action-platform}"

  [ "$(id -u)" -eq 0 ] || die "run as root (sudo sh install.sh)"
  if [ -n "$DOMAIN" ] && [ -z "$EMAIL" ]; then die "usage: install.sh [domain acme-email]"; fi
  if [ -n "$DOMAIN" ] && ! printf '%s' "$DOMAIN" | grep -Eq '^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$'; then die "domain: letters, digits, dots and hyphens only"; fi
  if [ -n "$EMAIL" ] && ! printf '%s' "$EMAIL" | grep -Eq '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'; then die "acme-email does not look like an address"; fi

  resolve_versions
  RAW="https://raw.githubusercontent.com/$REPO/refs/tags/api/v$API_VERSION/deploy"

  if ! command -v docker >/dev/null 2>&1; then
    say "installing Docker (get.docker.com, over TLS)"
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
  fi
  docker compose version >/dev/null 2>&1 || die "docker compose plugin missing"

  mkdir -p "$DIR"; cd "$DIR"
  umask 077

  if [ -f .env ] && [ -f docker-compose.yml ]; then
    CURRENT_API="$(image_version AP_IMAGE_API)"
    CURRENT_WEB="$(image_version AP_IMAGE_WEB)"
    say "api ${CURRENT_API:-unpinned} → $API_VERSION, web ${CURRENT_WEB:-unpinned} → $WEB_VERSION"
    if [ "$CURRENT_API" != "$API_VERSION" ] || [ "$CURRENT_WEB" != "$WEB_VERSION" ]; then
      backup_database
    fi
  else
    say "installing api $API_VERSION, web $WEB_VERSION"
  fi

  say "fetching compose files (api/v$API_VERSION)"
  curl -fsSL "$RAW/docker-compose.yml" -o docker-compose.yml.tmp
  curl -fsSL "$RAW/.env.example" -o .env.example.tmp
  mv docker-compose.yml.tmp docker-compose.yml
  mv .env.example.tmp .env.example

  mkdir -p secrets
  chmod 700 secrets
  for name in postgres_password better_auth_secret api_token; do
    if [ ! -s "secrets/$name" ]; then
      openssl rand -hex 32 > "secrets/$name"
    fi
    chmod 644 "secrets/$name"
  done

  if [ -f .env ]; then
    say "keeping existing .env"
  else
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
  fi
  set_env AP_IMAGE_API "$IMAGES-api:$API_VERSION"
  set_env AP_IMAGE_WORKER "$IMAGES-worker:$API_VERSION"
  set_env AP_IMAGE_WEB "$IMAGES-web:$WEB_VERSION"
  chmod 600 .env

  say "starting api $API_VERSION, web $WEB_VERSION"
  compose pull
  compose up -d

  URL="$(sed -n 's/^PUBLIC_URL=//p' .env)"
  echo
  say "Action Platform is up: $URL"
  setup_hint
  echo "  Files: $DIR   (secrets/ holds the secrets, .env the settings and image versions, backups/ the pre-upgrade dumps; docker compose logs -f to watch)"
}

[ "${AP_INSTALL_SOURCE_ONLY:-}" = 1 ] || main "$@"
