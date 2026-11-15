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
if grep -q "CHANGE-ME" .env.production; then
  echo "Replace every CHANGE-ME value in .env.production first."
  exit 1
fi

echo "== Updating code ($BRANCH)"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "== Building and starting containers"
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build --remove-orphans

echo "== Cleaning old images"
docker image prune -f >/dev/null

echo "== Status"
docker compose -f docker-compose.prod.yml --env-file .env.production ps
DOMAIN=$(grep '^DOMAIN=' .env.production | cut -d= -f2)
echo
echo "Done. Open https://$DOMAIN (the first HTTPS certificate can take a minute)."
echo "Logs: docker compose -f docker-compose.prod.yml --env-file .env.production logs -f"
