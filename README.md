# EveryStore

An open-source eCommerce platform for individual sellers. One command to deploy, runs on AWS Free Tier.

**Stack:** Django 5 · PostgreSQL · AWS S3 · PayPal · Docker Compose · nginx (HTTPS auto-configured)

---

## Quick Start

```bash
git clone https://github.com/Ori-irO-Ori/EveryStore.git
cd EveryStore
./setup.sh
docker compose up -d
```

That's it. On first run Docker will:
- Generate a random admin URL, port, and password — printed once to logs
- Run database migrations automatically
- Create the admin superuser
- Collect static files
- Start nginx with HTTPS (auto self-signed → Let's Encrypt if you set a domain)

**View admin credentials after first run:**
```bash
./manage.sh admin
```

---

## Installing Docker

### Ubuntu / Debian (including EC2)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Allow your user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Other Operating Systems

| OS | Link |
|----|------|
| macOS | [docs.docker.com/desktop/install/mac-install](https://docs.docker.com/desktop/install/mac-install/) |
| Windows | [docs.docker.com/desktop/install/windows-install](https://docs.docker.com/desktop/install/windows-install/) |
| Other Linux | [docs.docker.com/engine/install](https://docs.docker.com/engine/install/) |

---

## Configuration

Run `./setup.sh` — it will walk you through all options interactively and generate your `.env` file.

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (long random string) |
| `ALLOWED_HOSTS` | Your domain or EC2 public IP |
| `DB_PASS` | PostgreSQL password |
| `PAYPAL_CLIENT_ID` | PayPal app client ID |
| `PAYPAL_CLIENT_SECRET` | PayPal app client secret |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `everystore-db` | Use bundled postgres, or your RDS endpoint |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `everystore` | |
| `DB_USER` | `everystore` | |
| `DB_SSLMODE` | `disable` | Set to `require` for RDS |

### AWS S3 (Product Images)

Leave `S3_BUCKET` empty to use local storage instead.

| Variable | Description |
|----------|-------------|
| `S3_BUCKET` | S3 bucket name |
| `S3_REGION` | e.g. `us-east-1` |
| `S3_ACCESS_KEY` | IAM access key |
| `S3_SECRET_KEY` | IAM secret key |

> **S3 bucket setup:** Disable "Block all public access" and add this bucket policy:
> ```json
> {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::YOUR-BUCKET/*"}]}
> ```

### HTTPS / SSL

| Option | Variables needed | Result |
|--------|-----------------|--------|
| Let's Encrypt (recommended) | `DOMAIN` + `CERTBOT_EMAIL` | Auto cert, auto renewal |
| Custom certificate | `SSL_CERT_PATH` + `SSL_KEY_PATH` | Your own cert |
| Nothing set | — | Self-signed cert (browser warning) |

### Email (Order Confirmations)

| Variable | Example |
|----------|---------|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `465` |
| `EMAIL_HOST_USER` | `you@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Gmail App Password (no spaces) |
| `EMAIL_FROM` | `Your Store <you@gmail.com>` |

> **Gmail App Password:** Enable 2-Step Verification → [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### PayPal

| Variable | Description |
|----------|-------------|
| `PAYMENT_MODE` | `sandbox` for testing, `live` for real payments |
| `PAYPAL_CLIENT_ID` | From [developer.paypal.com](https://developer.paypal.com) |
| `PAYPAL_CLIENT_SECRET` | From PayPal developer dashboard |

### Store & Theme

| Variable | Default | Description |
|----------|---------|-------------|
| `STORE_NAME` | `EveryStore` | Displayed in header and emails |
| `STORE_CURRENCY` | `USD` | Currency code |
| `SELLER_CONTACT_TYPE` | `email` | `email` / `whatsapp` / `telegram` / `wechat` |
| `SELLER_CONTACT_VALUE` | — | Your contact info shown on storefront |
| `THEME_PRIMARY_COLOR` | `#6366f1` | Hex color for buttons and accents |
| `THEME_LOGO_URL` | — | Full URL to your logo image |
| `THEME_HERO_IMAGE_URL` | — | Full URL to homepage banner image |

---

## Deploying on AWS EC2 (Free Tier)

### Prerequisites
- EC2 instance (t2.micro or t3.micro, Ubuntu 22.04)
- Docker + Docker Compose installed
- Port 80, 443, and one random high port (10000–65000) open in Security Group
- RDS PostgreSQL (optional — bundled postgres works too)
- S3 bucket (optional — local storage works too)

### Steps

```bash
# 1. SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# 2. Install Docker (see Installing Docker section above)

# 3. Clone and configure
git clone https://github.com/Ori-irO-Ori/EveryStore.git
cd EveryStore
./setup.sh

# 4. Start
docker compose up -d

# 5. Get admin credentials (generated on first run)
./manage.sh admin
```

### Connecting to RDS

In `.env`:
```
DB_HOST=your-instance.abc123.us-east-1.rds.amazonaws.com
DB_USER=everystore
DB_PASS=your-rds-password
DB_SSLMODE=require
```

Make sure the RDS security group allows inbound TCP 5432 from the EC2 instance's security group.

---

## Management Scripts

Two helper scripts are included in the project root.

### `./setup.sh` — First-time configuration wizard

Walks you through every configuration option and generates your `.env` file interactively. Run this once before `docker compose up -d`.

```bash
./setup.sh
```

Covers: Django secret key, database (local or RDS), S3, PayPal (sandbox/live), SSL (Let's Encrypt / custom cert / self-signed), email (Gmail or custom SMTP), store name, contact info, and theme.

### `./manage.sh` — Admin management

```bash
# Show admin panel URL and credentials
./manage.sh admin

# Change the admin panel port (also updates the running container)
./manage.sh change-port

# Show help
./manage.sh help
```

### Updating to a new version

```bash
git pull
docker compose build everystore-app everystore-nginx
docker compose up -d
```

Your `.env`, database, and admin credentials are preserved — only the application code is updated.

---

## Architecture

```
Browser
  └── nginx (host network · port 80/443 + random admin port)
        └── gunicorn (127.0.0.1:8000 · 3 workers)
              └── Django 5
                    ├── PostgreSQL (RDS or bundled container)
                    └── S3 (media) · WhiteNoise (static)
```

- **Admin panel** runs on a random high port with a random URL path — generated on first run, credentials printed to logs
- **SSL** handled by nginx: Let's Encrypt → custom cert → self-signed fallback
- **Migrations** run automatically on every container start
- **Order confirmations** sent by email automatically after payment

---

## License

MIT
