# Deployment Guide

## Overview

This guide covers deploying the Google Contacts to Cisco IP Phone application to production environments. It includes Docker deployment, systemd service configuration, reverse proxy setup, SSL/TLS configuration, and monitoring.

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Docker Deployment](#docker-deployment)
3. [System Service Deployment](#system-service-deployment)
4. [Reverse Proxy Setup](#reverse-proxy-setup)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Production Configuration](#production-configuration)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Backup and Recovery](#backup-and-recovery)
9. [Security Hardening](#security-hardening)
10. [Performance Tuning](#performance-tuning)

---

## Deployment Options

### Option 1: Docker (Recommended)
- ✅ Easy deployment and updates
- ✅ Consistent environment
- ✅ Easy rollback
- ✅ Resource isolation

### Option 2: Systemd Service
- ✅ Native Linux integration
- ✅ Lower overhead
- ✅ Direct system access
- ⚠️ More configuration required

### Option 3: Kubernetes
- ✅ Enterprise-scale deployment
- ✅ Auto-scaling
- ✅ High availability
- ⚠️ More complex setup

This guide covers Options 1 and 2. For Kubernetes deployment, adapt the Docker configuration.

---

## Docker Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

### Step 1: Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock ./
COPY google_contacts_cisco ./google_contacts_cisco
COPY alembic ./alembic
COPY alembic.ini ./

# Install uv and dependencies
RUN pip install uv && \
    uv pip install --system -e .

# Create data directory
RUN mkdir -p /app/data && chmod 755 /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8000/health || exit 1

# Run migrations and start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn google_contacts_cisco.main:app --host 0.0.0.0 --port 8000"]
```

### Step 2: Create Docker Compose File

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: google-contacts-cisco
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    environment:
      - DATABASE_URL=sqlite:///./data/contacts.db
      - HOST=0.0.0.0
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - app-network

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: google-contacts-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### Step 3: Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Check status
docker-compose ps
```

### Step 4: Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Check auth status
curl http://localhost:8000/auth/status

# Test directory
curl http://localhost:8000/directory
```

### Docker Management

```bash
# Stop services
docker-compose stop

# Restart services
docker-compose restart

# Update application
git pull
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f app

# Execute commands in container
docker-compose exec app bash

# Remove containers (keeps data volume)
docker-compose down

# Remove everything including volumes
docker-compose down -v
```

---

## System Service Deployment

### Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.10+
- systemd
- Non-root user for running service

### Step 1: Create Application User

```bash
# Create dedicated user
sudo useradd -r -s /bin/false -m -d /opt/google-contacts-cisco contacts

# Create directories
sudo mkdir -p /opt/google-contacts-cisco
sudo mkdir -p /var/log/google-contacts-cisco

# Set ownership
sudo chown -R contacts:contacts /opt/google-contacts-cisco
sudo chown -R contacts:contacts /var/log/google-contacts-cisco
```

### Step 2: Install Application

```bash
# Clone repository
cd /opt/google-contacts-cisco
sudo -u contacts git clone https://github.com/rohankapoorcom/google-contacts-cisco.git .

# Install dependencies
sudo -u contacts python3 -m venv venv
sudo -u contacts /opt/google-contacts-cisco/venv/bin/pip install uv
sudo -u contacts /opt/google-contacts-cisco/venv/bin/uv pip install -e .

# Create data directory
sudo -u contacts mkdir -p /opt/google-contacts-cisco/data
```

### Step 3: Create Configuration

```bash
# Copy example config
sudo -u contacts cp .env.example .env

# Edit configuration
sudo -u contacts nano .env
```

Configuration for production:
```env
DATABASE_URL=sqlite:////opt/google-contacts-cisco/data/contacts.db
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback
HOST=127.0.0.1
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
SYNC_SCHEDULER_ENABLED=true
SYNC_INTERVAL_MINUTES=30
TOKEN_FILE=/opt/google-contacts-cisco/data/token.json
```

### Step 4: Run Database Migrations

```bash
sudo -u contacts /opt/google-contacts-cisco/venv/bin/alembic upgrade head
```

### Step 5: Create Systemd Service

Create `/etc/systemd/system/google-contacts-cisco.service`:

```ini
[Unit]
Description=Google Contacts to Cisco IP Phone Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=contacts
Group=contacts
WorkingDirectory=/opt/google-contacts-cisco
Environment="PATH=/opt/google-contacts-cisco/venv/bin"
EnvironmentFile=/opt/google-contacts-cisco/.env

ExecStart=/opt/google-contacts-cisco/venv/bin/gunicorn \
    google_contacts_cisco.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/google-contacts-cisco/access.log \
    --error-logfile /var/log/google-contacts-cisco/error.log \
    --log-level info

# Restart policy
Restart=on-failure
RestartSec=10s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/google-contacts-cisco/data /var/log/google-contacts-cisco
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

### Step 6: Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable google-contacts-cisco

# Start service
sudo systemctl start google-contacts-cisco

# Check status
sudo systemctl status google-contacts-cisco

# View logs
sudo journalctl -u google-contacts-cisco -f
```

### Service Management

```bash
# Start service
sudo systemctl start google-contacts-cisco

# Stop service
sudo systemctl stop google-contacts-cisco

# Restart service
sudo systemctl restart google-contacts-cisco

# Reload configuration
sudo systemctl reload google-contacts-cisco

# Check status
sudo systemctl status google-contacts-cisco

# View logs
sudo journalctl -u google-contacts-cisco --since today
sudo journalctl -u google-contacts-cisco -f  # Follow logs

# Disable auto-start
sudo systemctl disable google-contacts-cisco
```

---

## Reverse Proxy Setup

### Nginx Configuration

#### Step 1: Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

#### Step 2: Create Nginx Configuration

Create `/etc/nginx/sites-available/google-contacts-cisco`:

```nginx
# HTTP server (redirect to HTTPS)
server {
    listen 80;
    listen [::]:80;
    server_name contacts.yourdomain.com;

    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name contacts.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/contacts.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/contacts.yourdomain.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/contacts.yourdomain.com/chain.pem;

    # SSL settings (modern configuration)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/google-contacts-access.log;
    error_log /var/log/nginx/google-contacts-error.log;

    # Root location (Vue frontend)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # Auth endpoints
    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Directory endpoints (for Cisco phones)
    location /directory/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Caching for directory (5 minutes)
        proxy_cache_valid 200 5m;
        proxy_cache_bypass $http_cache_control;
        add_header X-Cache-Status $upstream_cache_status;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
```

#### Step 3: Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/google-contacts-cisco /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Apache Configuration (Alternative)

Create `/etc/apache2/sites-available/google-contacts-cisco.conf`:

```apache
<VirtualHost *:80>
    ServerName contacts.yourdomain.com
    Redirect permanent / https://contacts.yourdomain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName contacts.yourdomain.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/contacts.yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/contacts.yourdomain.com/privkey.pem

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    ErrorLog ${APACHE_LOG_DIR}/google-contacts-error.log
    CustomLog ${APACHE_LOG_DIR}/google-contacts-access.log combined
</VirtualHost>
```

Enable modules and site:
```bash
sudo a2enmod proxy proxy_http ssl headers
sudo a2ensite google-contacts-cisco
sudo systemctl reload apache2
```

---

## SSL/TLS Configuration

### Using Let's Encrypt (Recommended)

#### Step 1: Install Certbot

```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# Or for Apache
sudo apt install certbot python3-certbot-apache
```

#### Step 2: Obtain Certificate

```bash
# For Nginx
sudo certbot --nginx -d contacts.yourdomain.com

# For Apache
sudo certbot --apache -d contacts.yourdomain.com

# Manual (if you want to configure yourself)
sudo certbot certonly --standalone -d contacts.yourdomain.com
```

#### Step 3: Test Auto-Renewal

```bash
# Dry run
sudo certbot renew --dry-run

# Renewal happens automatically via systemd timer
sudo systemctl status certbot.timer
```

### Using Self-Signed Certificate (Development Only)

```bash
# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/google-contacts-selfsigned.key \
  -out /etc/ssl/certs/google-contacts-selfsigned.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=contacts.yourdomain.com"

# Update Nginx configuration to use it
ssl_certificate /etc/ssl/certs/google-contacts-selfsigned.crt;
ssl_certificate_key /etc/ssl/private/google-contacts-selfsigned.key;
```

**Note**: Self-signed certificates will show warnings in browsers and may not work with Cisco phones without importing the CA certificate.

---

## Production Configuration

### Environment Variables

Production `.env` file:

```env
# Application
APP_NAME=Google Contacts Cisco
DEBUG=false
LOG_LEVEL=INFO

# Server
HOST=127.0.0.1  # Only listen on localhost (nginx will proxy)
PORT=8000

# Database
DATABASE_URL=sqlite:////opt/google-contacts-cisco/data/contacts.db

# Google OAuth
GOOGLE_CLIENT_ID=your-production-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-production-client-secret
GOOGLE_REDIRECT_URI=https://contacts.yourdomain.com/auth/callback

# Token storage
TOKEN_FILE=/opt/google-contacts-cisco/data/token.json

# Sync scheduler
SYNC_SCHEDULER_ENABLED=true
SYNC_INTERVAL_MINUTES=30

# Security
# Add any additional security settings here
```

### File Permissions

```bash
# Set secure permissions
sudo chmod 600 /opt/google-contacts-cisco/.env
sudo chmod 700 /opt/google-contacts-cisco/data
sudo chmod 600 /opt/google-contacts-cisco/data/token.json
sudo chmod 644 /opt/google-contacts-cisco/data/contacts.db

# Verify ownership
sudo chown -R contacts:contacts /opt/google-contacts-cisco
```

### Workers and Performance

For production with Gunicorn, calculate workers:

```bash
# Formula: (2 x CPU cores) + 1
# Example for 4 CPU cores: (2 x 4) + 1 = 9 workers

# Update systemd service
ExecStart=/opt/google-contacts-cisco/venv/bin/gunicorn \
    google_contacts_cisco.main:app \
    --workers 9 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000
```

---

## Monitoring and Logging

### Application Logs

```bash
# View application logs
sudo journalctl -u google-contacts-cisco -f

# View errors only
sudo journalctl -u google-contacts-cisco -p err

# View logs from last hour
sudo journalctl -u google-contacts-cisco --since "1 hour ago"

# Export logs
sudo journalctl -u google-contacts-cisco > app.log
```

### Log Rotation

Create `/etc/logrotate.d/google-contacts-cisco`:

```logrotate
/var/log/google-contacts-cisco/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 contacts contacts
    sharedscripts
    postrotate
        systemctl reload google-contacts-cisco > /dev/null 2>&1 || true
    endscript
}
```

### Health Monitoring

Create monitoring script `/usr/local/bin/check-google-contacts-health.sh`:

```bash
#!/bin/bash

HEALTH_URL="http://localhost:8000/health"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

if [ "$STATUS" -ne 200 ]; then
    echo "Health check failed! HTTP status: $STATUS"
    systemctl restart google-contacts-cisco
    # Send alert (email, Slack, etc.)
    exit 1
fi

echo "Health check OK"
exit 0
```

Add to crontab:
```bash
# Run health check every 5 minutes
*/5 * * * * /usr/local/bin/check-google-contacts-health.sh
```

### Performance Monitoring

Install and configure monitoring tools:

```bash
# Install Prometheus node exporter
sudo apt install prometheus-node-exporter

# Install monitoring dashboard (optional)
# Grafana, Prometheus, etc.
```

---

## Backup and Recovery

### Database Backup

Create backup script `/usr/local/bin/backup-google-contacts.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/var/backups/google-contacts-cisco"
DATA_DIR="/opt/google-contacts-cisco/data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 "$DATA_DIR/contacts.db" ".backup '$BACKUP_DIR/contacts_$TIMESTAMP.db'"

# Backup token file
cp "$DATA_DIR/token.json" "$BACKUP_DIR/token_$TIMESTAMP.json"

# Backup configuration
cp "/opt/google-contacts-cisco/.env" "$BACKUP_DIR/env_$TIMESTAMP"

# Compress backup
tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" \
    "contacts_$TIMESTAMP.db" "token_$TIMESTAMP.json" "env_$TIMESTAMP"

# Remove uncompressed files
rm "$BACKUP_DIR/contacts_$TIMESTAMP.db" \
   "$BACKUP_DIR/token_$TIMESTAMP.json" \
   "$BACKUP_DIR/env_$TIMESTAMP"

# Keep only last 30 days
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: backup_$TIMESTAMP.tar.gz"
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-google-contacts.sh
```

### Restore from Backup

```bash
# Stop service
sudo systemctl stop google-contacts-cisco

# Extract backup
tar -xzf /var/backups/google-contacts-cisco/backup_20260108_020000.tar.gz -C /tmp

# Restore database
cp /tmp/contacts_20260108_020000.db /opt/google-contacts-cisco/data/contacts.db

# Restore token
cp /tmp/token_20260108_020000.json /opt/google-contacts-cisco/data/token.json

# Fix permissions
sudo chown contacts:contacts /opt/google-contacts-cisco/data/*
sudo chmod 600 /opt/google-contacts-cisco/data/token.json
sudo chmod 644 /opt/google-contacts-cisco/data/contacts.db

# Start service
sudo systemctl start google-contacts-cisco
```

---

## Security Hardening

### Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow from Cisco phone subnet only (example)
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Enable firewall
sudo ufw enable
```

### Fail2Ban Configuration

Protect against brute force attacks:

```bash
# Install fail2ban
sudo apt install fail2ban

# Create jail for application
sudo nano /etc/fail2ban/jail.d/google-contacts.conf
```

```ini
[google-contacts]
enabled = true
port = http,https
filter = google-contacts
logpath = /var/log/nginx/google-contacts-access.log
maxretry = 5
bantime = 3600
findtime = 600
```

### Application Security

1. **Run as Non-Root User** ✓ (configured in systemd service)

2. **Disable Debug Mode** ✓ (DEBUG=false in .env)

3. **Secure File Permissions** ✓
   ```bash
   chmod 600 .env data/token.json
   chmod 700 data/
   ```

4. **Use HTTPS** ✓ (configured in nginx)

5. **Rate-Limiting** (future enhancement)
   - Add rate-limiting middleware
   - Or use nginx rate-limiting

6. **Security Headers** ✓ (configured in nginx)

---

## Performance Tuning

### Database Optimization

```bash
# Run VACUUM to optimize database
sqlite3 /opt/google-contacts-cisco/data/contacts.db "VACUUM;"

# Analyze database
sqlite3 /opt/google-contacts-cisco/data/contacts.db "ANALYZE;"

# Add to cron (monthly)
0 3 1 * * sqlite3 /opt/google-contacts-cisco/data/contacts.db "VACUUM; ANALYZE;"
```

### Nginx Caching

Add caching for directory requests:

```nginx
# In http block
proxy_cache_path /var/cache/nginx/google-contacts levels=1:2 keys_zone=contacts_cache:10m max_size=100m inactive=60m;

# In location /directory/
location /directory/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_cache contacts_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
}
```

### System Resources

Monitor and optimize:

```bash
# Check memory usage
free -h

# Check disk usage
df -h

# Check CPU usage
top

# Check application resource usage
systemctl status google-contacts-cisco
```

---

## Troubleshooting Deployment

### Service Won't Start

```bash
# Check status
sudo systemctl status google-contacts-cisco

# Check logs
sudo journalctl -u google-contacts-cisco -n 100

# Test application manually
cd /opt/google-contacts-cisco
sudo -u contacts ./venv/bin/uvicorn google_contacts_cisco.main:app
```

### Nginx Issues

```bash
# Test configuration
sudo nginx -t

# Check error log
sudo tail -f /var/log/nginx/error.log

# Restart nginx
sudo systemctl restart nginx
```

### SSL Certificate Issues

```bash
# Test certificate
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Check certificate expiry
echo | openssl s_client -servername contacts.yourdomain.com -connect contacts.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

For more troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).

---

## Conclusion

This deployment guide covers the essential aspects of deploying the Google Contacts to Cisco IP Phone application to production. Key points:

- ✅ Multiple deployment options (Docker, systemd)
- ✅ Reverse proxy configuration (Nginx/Apache)
- ✅ SSL/TLS setup with Let's Encrypt
- ✅ Production configuration and security
- ✅ Monitoring and logging
- ✅ Backup and recovery procedures
- ✅ Performance optimization

For additional help:
- [Setup Guide](setup.md) - Initial setup and configuration
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [API Documentation](api.md) - API reference
