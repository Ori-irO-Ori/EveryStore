#!/bin/bash
set -e

SECRETS_FILE="/app/secrets/admin.env"
mkdir -p /app/secrets

# ── First-time setup: generate admin credentials ──────────────────────────────
if [ ! -f "$SECRETS_FILE" ]; then
    ADMIN_PORT=$(python3 -c "import random; print(random.randint(10000, 65000))")
    ADMIN_PASSWORD=$(python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits
print(''.join(secrets.choice(chars) for _ in range(28)))
")
    ADMIN_URL_PATH=$(python3 -c "import secrets; print(secrets.token_hex(8))")

    # Use printf %q to safely quote values — prevents special chars from breaking `source`
    {
        printf 'ADMIN_PORT=%q\n' "$ADMIN_PORT"
        printf 'ADMIN_PASSWORD=%q\n' "$ADMIN_PASSWORD"
        printf 'ADMIN_URL_PATH=%q\n' "$ADMIN_URL_PATH"
    } > "$SECRETS_FILE"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║              EveryStore — First Time Setup                      ║"
    echo "║  SAVE THESE CREDENTIALS — they will NOT be shown again!         ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    printf "║  Admin Port:      %-47s║\n" "${ADMIN_PORT}"
    printf "║  Admin Path:      /%-46s║\n" "${ADMIN_URL_PATH}/"
    printf "║  Admin Username:  %-47s║\n" "admin"
    printf "║  Admin Password:  %-47s║\n" "${ADMIN_PASSWORD}"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    printf "║  Admin URL:  https://YOUR_IP:%-37s║\n" "${ADMIN_PORT}/${ADMIN_URL_PATH}/"
    echo "║  ⚠  Open port ${ADMIN_PORT} in your AWS Security Group!              ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
fi

# Load secrets into environment
source "$SECRETS_FILE"
export ADMIN_PORT ADMIN_PASSWORD ADMIN_URL_PATH

# ── Wait for database ─────────────────────────────────────────────────────────
echo "[app] Waiting for database..."
python3 << 'PYEOF'
import time, os, sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'everystore.settings')
django.setup()
from django.db import connections
from django.db.utils import OperationalError
for attempt in range(60):
    try:
        connections['default'].ensure_connection()
        print("[app] Database is ready.")
        sys.exit(0)
    except OperationalError:
        print(f"[app] Database not ready, retrying... ({attempt+1}/60)")
        time.sleep(2)
print("[app] ERROR: Could not connect to database after 120s.")
sys.exit(1)
PYEOF

# ── Django setup ──────────────────────────────────────────────────────────────
echo "[app] Running migrations..."
python manage.py migrate --noinput

echo "[app] Collecting static files..."
python manage.py collectstatic --noinput --clear -v 0

# ── Create superuser ──────────────────────────────────────────────────────────
echo "[app] Setting up admin user..."
DJANGO_ADMIN_PASSWORD="$ADMIN_PASSWORD" python3 manage.py shell << 'PYEOF'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
password = os.environ['DJANGO_ADMIN_PASSWORD']
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@everystore.local', password)
    print("[app] Superuser 'admin' created.")
else:
    print("[app] Superuser 'admin' already exists.")
PYEOF

# ── Start Gunicorn ────────────────────────────────────────────────────────────
echo "[app] Starting Gunicorn..."
exec gunicorn everystore.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class gthread \
    --threads 2 \
    --timeout 60 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
