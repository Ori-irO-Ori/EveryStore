#!/bin/bash
set -e

SECRETS_FILE="/app/secrets/admin.env"
CERT_DIR="/app/secrets/certs"
mkdir -p "$CERT_DIR"

# ── Wait for the app container to generate admin secrets ──────────────────────
echo "[nginx] Waiting for admin secrets from app container..."
for i in $(seq 1 60); do
    [ -f "$SECRETS_FILE" ] && break
    sleep 2
done
if [ ! -f "$SECRETS_FILE" ]; then
    echo "[nginx] ERROR: admin secrets file never appeared. Is everystore-app running?"
    exit 1
fi
set +e   # temporarily allow errors during source
# shellcheck disable=SC1090
source "$SECRETS_FILE"
set -e
export ADMIN_PORT ADMIN_URL_PATH

# ── Determine SSL certificate to use ─────────────────────────────────────────
SSL_MODE="none"
CERT_FILE=""
KEY_FILE=""

if [ -n "$SSL_CERT_PATH" ] && [ -f "$SSL_CERT_PATH" ]; then
    # Option A: user-provided certificate
    SSL_MODE="custom"
    CERT_FILE="$SSL_CERT_PATH"
    KEY_FILE="$SSL_KEY_PATH"
    echo "[nginx] Using custom SSL certificate: $SSL_CERT_PATH"

elif [ -n "$DOMAIN" ] && [ -n "$CERTBOT_EMAIL" ]; then
    # Option B: Let's Encrypt (only when a real domain is provided, not an IP)
    if echo "$DOMAIN" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
        echo "[nginx] DOMAIN looks like an IP address — skipping Let's Encrypt."
    else
        LE_CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
        LE_KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"

        if [ -f "$LE_CERT" ]; then
            echo "[nginx] Existing Let's Encrypt certificate found."
        else
            echo "[nginx] Requesting Let's Encrypt certificate for $DOMAIN ..."
            # Temporarily start nginx on port 80 for the HTTP-01 challenge
            mkdir -p /var/www/certbot/.well-known/acme-challenge
            envsubst '${DOMAIN} ${ADMIN_PORT} ${ADMIN_URL_PATH}' \
                < /etc/nginx/templates/http-challenge.conf.template \
                > /etc/nginx/conf.d/default.conf
            nginx &
            NGINX_PID=$!
            sleep 2

            certbot certonly \
                --webroot \
                --webroot-path /var/www/certbot \
                --non-interactive \
                --agree-tos \
                --email "$CERTBOT_EMAIL" \
                -d "$DOMAIN" \
                -d "www.$DOMAIN" 2>/dev/null \
            || certbot certonly \
                --webroot \
                --webroot-path /var/www/certbot \
                --non-interactive \
                --agree-tos \
                --email "$CERTBOT_EMAIL" \
                -d "$DOMAIN" 2>/dev/null \
            || echo "[nginx] Let's Encrypt failed — falling back to self-signed cert."

            kill $NGINX_PID 2>/dev/null || true
            sleep 1
        fi

        if [ -f "$LE_CERT" ]; then
            SSL_MODE="letsencrypt"
            CERT_FILE="$LE_CERT"
            KEY_FILE="$LE_KEY"
            echo "[nginx] Let's Encrypt certificate ready."

            # Schedule auto-renewal (runs every 12 hours in the background)
            (while true; do
                sleep 43200
                echo "[nginx] Renewing Let's Encrypt certificate..."
                certbot renew --quiet --webroot --webroot-path /var/www/certbot
                nginx -s reload
            done) &
        fi
    fi
fi

# Option C: self-signed fallback if nothing else worked
if [ "$SSL_MODE" = "none" ]; then
    CERT_FILE="$CERT_DIR/selfsigned.crt"
    KEY_FILE="$CERT_DIR/selfsigned.key"
    if [ ! -f "$CERT_FILE" ]; then
        echo "[nginx] Generating self-signed SSL certificate (valid 365 days)..."
        CN="${DOMAIN:-localhost}"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$KEY_FILE" \
            -out "$CERT_FILE" \
            -subj "/C=US/ST=State/L=City/O=EveryStore/CN=$CN" \
            -addext "subjectAltName=DNS:$CN,IP:127.0.0.1" 2>/dev/null
        echo "[nginx] Self-signed cert generated. HTTPS is active (browser warning expected)."
        echo "[nginx] Set DOMAIN + CERTBOT_EMAIL in .env to get a trusted Let's Encrypt cert."
    fi
    SSL_MODE="selfsigned"
fi

export CERT_FILE KEY_FILE

# ── Generate final nginx config ───────────────────────────────────────────────
echo "[nginx] Writing nginx configuration (SSL_MODE=$SSL_MODE, ADMIN_PORT=$ADMIN_PORT)..."

DOMAIN="${DOMAIN:-_}"
export DOMAIN

envsubst '${DOMAIN} ${ADMIN_PORT} ${ADMIN_URL_PATH} ${CERT_FILE} ${KEY_FILE}' \
    < /etc/nginx/templates/nginx.conf.template \
    > /etc/nginx/conf.d/default.conf

# Remove default nginx config to avoid conflicts
rm -f /etc/nginx/conf.d/default.conf.bak /etc/nginx/sites-enabled/default 2>/dev/null || true

echo "[nginx] Starting nginx..."
exec nginx -g 'daemon off;'
