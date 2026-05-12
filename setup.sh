#!/usr/bin/env bash
# Friday – local dev setup
# Prerequisites: Python 3.12+, PostgreSQL 16 (native), Redis 7 (native)
set -e

echo "── Creating virtualenv ──"
python3.12 -m venv .venv
source .venv/bin/activate

echo "── Installing dependencies ──"
pip install --upgrade pip
pip install -r requirements/development.txt

echo "── Creating .env from example ──"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  → .env created. Fill in your values before running the server."
fi

echo "── Creating PostgreSQL database ──"
createdb friday 2>/dev/null || echo "  → DB 'friday' already exists, skipping."

echo "── Running migrations ──"
python manage.py migrate

echo "── Creating superuser ──"
python manage.py createsuperuser --noinput \
  --username admin --email admin@example.com 2>/dev/null || true

echo "── Seeding AI config from .env ──"
python manage.py seed_ai_config

echo ""
echo "✓ Setup complete."
echo "  Start dev server:  source .venv/bin/activate && python manage.py runserver"
echo "  Start Celery:      celery -A config worker --loglevel=info"
echo "  Start Beat:        celery -A config beat --loglevel=info"
