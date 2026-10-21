# 🚀 TechClub — Production Go-Live Deployment Checklist

This document is the official step-by-step checklist to take the **TechClub** platform from local development/staging to **live production** on your public domain (e.g. `techclub.so`).

---

## 📋 Pre-Flight Overview

| Area | Development / Local | Required for Live Production | Status |
| :--- | :--- | :--- | :---: |
| **Debug Mode** | `DEBUG = True` | `DJANGO_DEBUG = False` | ⏳ Must toggle in `.env` |
| **Secret Key** | Insecure default | 50+ char random cryptographic string | ⏳ Must generate |
| **Allowed Hosts** | `127.0.0.1, localhost` | `techclub.so, www.techclub.so, your_server_ip` | ⏳ Must set |
| **Email Backend** | Console (`terminal`) | SMTP (Resend / SendGrid / AWS SES / Gmail) | ⏳ Must set credentials |
| **Web Server** | `python manage.py runserver` | **Gunicorn** or **Uvicorn** + **Nginx** reverse proxy | ⏳ Must configure |
| **SSL / HTTPS** | Plain HTTP (`http://`) | Let's Encrypt SSL (`https://`) | ⏳ Must install cert |
| **Database** | Local PostgreSQL 18 | Production PostgreSQL with automated backups | ⏳ Must configure |
| **Static Files** | Served by Django runserver | `collectstatic` + Nginx / WhiteNoise | ⏳ Must collect |
| **Media Files** | Local `media/` folder | Persistent SSD volume or AWS S3 / DO Spaces | ⏳ Must persist |

---

## 1. Environment Variables & Security Configuration

Create a secure `.env` file on your production server (never commit this file to public Git):

```ini
# --- Django Core ---
DJANGO_DEBUG=False
SECRET_KEY=django-insecure-CHANGE-THIS-TO-A-RANDOM-50-CHAR-STRING-FOR-PRODUCTION
ALLOWED_HOSTS=techclub.so,www.techclub.so,127.0.0.1

# --- PostgreSQL Database ---
DB_NAME=techclub_prod_db
DB_USER=techclub_admin
DB_PASSWORD=YOUR_STRONG_PROD_DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=5432

# --- Transactional Email (SMTP) ---
# Supports Resend, SendGrid, Amazon SES, or Google Workspace
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=re_Your_Production_API_Key
DEFAULT_FROM_EMAIL=TechClub Admissions <admissions@techclub.so>
```

> **Security Note:** Generating a secure `SECRET_KEY` in python:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## 2. Production Database & Migrations

- [ ] **Provision PostgreSQL Instance:** Ensure PostgreSQL 15+ is installed and running with UTF-8 encoding.
- [ ] **Create Database & Dedicated User:**
  ```sql
  CREATE DATABASE techclub_prod_db ENCODING 'UTF8';
  CREATE USER techclub_admin WITH ENCRYPTED PASSWORD 'YOUR_STRONG_PROD_DB_PASSWORD';
  GRANT ALL PRIVILEGES ON DATABASE techclub_prod_db TO techclub_admin;
  ```
- [ ] **Run Migrations on Server:**
  ```bash
  python manage.py migrate
  ```
- [ ] **Automated Daily Backups:** Set up a daily cron job to dump database backups:
  ```bash
  # Daily backup at 03:00 AM
  0 3 * * * pg_dump -U techclub_admin techclub_prod_db | gzip > /var/backups/techclub/db_$(date +\%F).sql.gz
  ```

---

## 3. Administrator & Seed Account Management

- [ ] **Create Real Organizer Account:**
  ```bash
  python manage.py createsuperuser
  ```
  *Make sure to assign `is_organizer = True` in Django admin or via seed script.*
- [ ] **Change Initial Passwords:** If you ran `seed_data.py`, immediately change the default `adminpass123` password for all seeded accounts via `/admin-ops/users/` or `/accounts/forgot-password/`.
- [ ] **Deactivate / Delete Unneeded Test Accounts:** Ensure only real organizers and active members exist in production.

---

## 4. Transactional Email & Domain Deliverability

TechClub relies on automated emails for **community applicant welcome notifications**, **password reset OTP codes**, and **event ticket passes**.

- [ ] **Configure DNS SPF Record:**
  `v=spf1 include:_spf.resend.com ~all` (or your chosen provider).
- [ ] **Configure DKIM & DMARC Records:**
  `v=DMARC1; p=quarantine; pct=100; rua=mailto:dmarc-reports@techclub.so`
- [ ] **Test Email Delivery:**
  Trigger a password recovery request at `/accounts/forgot-password/` and confirm receipt of the 6-digit OTP code in your inbox (not in spam).

---

## 5. Web Server & Process Management (Gunicorn + Systemd)

Never use `python manage.py runserver` in production.

- [ ] **Install Gunicorn:**
  ```bash
  pip install gunicorn
  ```
- [ ] **Create Systemd Service (`/etc/systemd/system/techclub.service`):**
  ```ini
  [Unit]
  Description=TechClub Gunicorn Application Server
  After=network.target

  [Service]
  User=ubuntu
  Group=www-data
  WorkingDirectory=/var/www/TechClub
  EnvironmentFile=/var/www/TechClub/.env
  ExecStart=/var/www/TechClub/venv/bin/gunicorn \
            --workers 3 \
            --bind 127.0.0.1:8000 \
            --access-logfile /var/log/techclub/access.log \
            --error-logfile /var/log/techclub/error.log \
            techclub_core.wsgi:application
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```
- [ ] **Enable and Start Service:**
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable techclub
  sudo systemctl start techclub
  ```

---

## 6. Reverse Proxy, Static Files & SSL (Nginx)

- [ ] **Collect Static Assets:**
  ```bash
  python manage.py collectstatic --noinput
  ```
- [ ] **Nginx Server Configuration (`/etc/nginx/sites-available/techclub`):**
  ```nginx
  server {
      server_name techclub.so www.techclub.so;

      client_max_body_size 25M;

      # Static files
      location /static/ {
          alias /var/www/TechClub/staticfiles/;
          expires 30d;
          add_header Cache-Control "public, no-transform";
      }

      # Media files (Event materials, Certificates, Profile photos)
      location /media/ {
          alias /var/www/TechClub/media/;
          expires 7d;
      }

      # Forward dynamic requests to Gunicorn
      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```
- [ ] **Install Free SSL via Let's Encrypt:**
  ```bash
  sudo apt install certbot python3-certbot-nginx
  sudo certbot --nginx -d techclub.so -d www.techclub.so
  ```

---

## 7. Media Persistence (Course Materials & Profile Photos)

- [ ] **Directory Permissions:** Ensure the `media/` directory is writable by the web service user:
  ```bash
  sudo chown -R ubuntu:www-data /var/www/TechClub/media
  sudo chmod -R 775 /var/www/TechClub/media
  ```
- [ ] **Backups for User Uploads:** Include `/var/www/TechClub/media` in regular file backups so uploaded certificates and slides are preserved across system updates.

---

## 8. Post-Launch Smoke Test Checklist

Once the domain points to your live server, execute these real-world tests:

- [ ] **Homepage & Public Pages:** Load `https://techclub.so/` (verify logo, styles, and hero load fast over HTTPS).
- [ ] **Public Events & RSVP:** Browse to `/events/` and register a test guest for an upcoming gathering.
- [ ] **Digital Ticket & QR Code:** Open the digital pass, verify the SVG QR code renders, and test copying the Zoom passcode.
- [ ] **Instant Live Check-in:** Test clicking "Join Live Class" and verify the official Certificate unlocks automatically.
- [ ] **Public Certificate Verification:** Open `/verify/<certificate_id>/` and check that the verified credential screen appears.
- [ ] **Course Materials Download:** Test downloading an attached PDF or slide deck and verify the download counter increments.
- [ ] **Community Application Submission:** Submit an application from `/apply/` and verify it lands in `/admin-ops/applications/`.
- [ ] **Organizer Sign In & Scanner:** Log in as organizer at `/accounts/login/` and open `/admin-ops/scan-ticket/` to test camera QR scanning.
- [ ] **Password Reset (OTP):** Request a reset at `/accounts/forgot-password/` and complete the OTP reset workflow.
