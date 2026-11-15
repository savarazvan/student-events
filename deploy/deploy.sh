#!/usr/bin/env sh
# Deploy or update the app on the VPS:  sh deploy/deploy.sh [branch]
# Pulls the latest code, rebuilds the images and restarts the stack.
set -eu

cd "$(dirname "$0")/.."
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"

if [ ! -f .env.production ]; then
  echo "Missing .env.production. Create it first:"
  echo "  cp .env.production.example .env.production && nano .env.production"
  exit 1
fi
# Only look at values (KEY=CHANGE-ME), not at the explanatory comments.
if grep -qE '^[A-Z_]+=CHANGE-ME' .env.production; then
  echo "Replace every CHANGE-ME value in .env.production first:"
  grep -nE '^[A-Z_]+=CHANGE-ME' .env.production
  exit 1
fi

COMPOSE="docker compose -f docker-compose.prod.yml"
if grep -q '^BEHIND_HOST_PROXY=true' .env.production; then
  COMPOSE="$COMPOSE -f docker-compose.proxy.yml"
fi
COMPOSE="$COMPOSE --env-file .env.production"

echo "== Updating code ($BRANCH)"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "== Building and starting containers"
$COMPOSE up -d --build --remove-orphans

echo "== Cleaning old images"
docker image prune -f >/dev/null

echo "== Status"
$COMPOSE ps
DOMAIN=$(grep '^DOMAIN=' .env.production | cut -d= -f2)
echo
if grep -q '^BEHIND_HOST_PROXY=true' .env.production; then
  PORT=$(grep '^WEB_PORT=' .env.production | cut -d= -f2)
  echo "App listening on 127.0.0.1:${PORT:-8081}. The host web server must proxy $DOMAIN to it"
  echo "(Caddy: see deploy/host-caddy.snippet)."
fi
echo "Done. Open https://$DOMAIN (the first HTTPS certificate can take a minute)."
echo "Logs: $COMPOSE logs -f"
