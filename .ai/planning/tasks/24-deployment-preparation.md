# Task 8.2: Deployment Preparation

## Overview

Prepare the application for production deployment with Docker containerization, environment configuration, production optimizations, backup strategies, and deployment automation.

## Priority

**P1 (High)** - Required for production deployment

## Dependencies

- All implementation tasks (1-22)
- Task 8.1: API Documentation

## Objectives

1. Create production Dockerfile with multi-stage build
2. Create docker-compose for full stack
3. Configure production environment variables
4. Set up production logging and monitoring
5. Implement database backup strategy
6. Create deployment scripts
7. Configure reverse proxy (nginx)
8. Add health checks and readiness probes
9. Document deployment procedures
10. Test complete deployment process

## Technical Context

### Deployment Architecture
```
[Internet] → [Nginx Reverse Proxy] → [FastAPI + Vue (Container)]
                                            ↓
                                        [SQLite Volume]
```

### Production Requirements
- Python 3.10+
- Node.js 18+ (for building frontend)
- Docker 20.10+
- 512MB RAM minimum
- 5GB disk space
- HTTPS certificate (Let's Encrypt recommended)

## Acceptance Criteria

- [ ] Multi-stage Dockerfile builds successfully
- [ ] Docker compose orchestrates all services
- [ ] Environment variables properly configured
- [ ] Production logging configured
- [ ] Health checks working
- [ ] Database backups automated
- [ ] Nginx reverse proxy configured
- [ ] HTTPS/TLS configured
- [ ] Deployment scripts tested
- [ ] Rollback procedure documented
- [ ] Monitoring hooks in place

## Implementation Steps

### 1. Create Multi-Stage Dockerfile

Create `Dockerfile`:

```dockerfile
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Build backend
FROM python:3.10-slim AS backend-builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml ./
COPY google_contacts_cisco/_version.py ./google_contacts_cisco/

# Install dependencies
RUN uv sync --frozen --no-dev

# Stage 3: Production image
FROM python:3.10-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Copy uv and dependencies from builder
COPY --from=backend-builder /root/.local /root/.local
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy application code
COPY --chown=appuser:appuser google_contacts_cisco ./google_contacts_cisco

# Copy frontend build
COPY --from=frontend-builder --chown=appuser:appuser /frontend/dist ./google_contacts_cisco/static/dist

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:$PATH"

# Run application
CMD ["uv", "run", "uvicorn", "google_contacts_cisco.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-config", "/app/logging.conf"]
```

### 2. Create Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: contacts-app
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # Only expose on localhost
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro  # Read-only config
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=sqlite:///data/contacts.db
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - OAUTH_REDIRECT_URI=${OAUTH_REDIRECT_URI}
      - LOG_LEVEL=INFO
      - CORS_ORIGINS=${CORS_ORIGINS}
    env_file:
      - .env.production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    container_name: contacts-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    networks:
      - app-network

  backup:
    image: alpine:latest
    container_name: contacts-backup
    restart: "no"
    volumes:
      - ./data:/data:ro
      - ./backups:/backups
    command: >
      sh -c "tar czf /backups/backup-$$(date +%Y%m%d-%H%M%S).tar.gz /data &&
             find /backups -name 'backup-*.tar.gz' -mtime +7 -delete"

networks:
  app-network:
    driver: bridge

volumes:
  data:
  logs:
```

### 3. Create Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=directory:10m rate=200r/m;

    upstream app_backend {
        server app:8000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name your-domain.com;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API endpoints with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Cisco directory endpoints
        location /directory/ {
            limit_req zone=directory burst=50 nodelay;
            
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Static files (Vue frontend)
        location /assets/ {
            proxy_pass http://app_backend;
            proxy_cache_valid 200 1h;
            add_header Cache-Control "public, immutable";
        }

        # All other routes (SPA)
        location / {
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 4. Create Environment Configuration

Create `.env.production.example`:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///data/contacts.db

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
OAUTH_REDIRECT_URI=https://your-domain.com/auth/callback

# Application Settings
CORS_ORIGINS=https://your-domain.com
DIRECTORY_TITLE="Company Contacts"

# Optional: Performance
UVICORN_WORKERS=2
UVICORN_TIMEOUT=60
```

### 5. Create Deployment Scripts

Create `scripts/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "===== Google Contacts Cisco Deployment ====="

# Configuration
ENV_FILE=".env.production"
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d-%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Check environment file
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found"
    echo "Please copy .env.production.example to .env.production and configure"
    exit 1
fi

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
mkdir -p "$BACKUP_DIR"
if [ -d "./data" ]; then
    tar czf "$BACKUP_DIR/pre-deploy-$DATE.tar.gz" ./data
    echo -e "${GREEN}Backup created: $BACKUP_DIR/pre-deploy-$DATE.tar.gz${NC}"
fi

# Build frontend
echo -e "${YELLOW}Building frontend...${NC}"
cd frontend
npm ci
npm run build
cd ..

# Build and start containers
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose -f docker-compose.prod.yml build

echo -e "${YELLOW}Starting containers...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Wait for healthcheck
echo -e "${YELLOW}Waiting for application to be healthy...${NC}"
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml ps | grep -q "healthy"; then
        echo -e "${GREEN}Application is healthy!${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Show status
echo -e "\n${YELLOW}Deployment Status:${NC}"
docker-compose -f docker-compose.prod.yml ps

# Show logs
echo -e "\n${YELLOW}Recent logs:${NC}"
docker-compose -f docker-compose.prod.yml logs --tail=20

echo -e "\n${GREEN}Deployment complete!${NC}"
echo "Access the application at: https://your-domain.com"
echo "View logs: docker-compose -f docker-compose.prod.yml logs -f"
```

Create `scripts/backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d-%H%M%S)
RETENTION_DAYS=30

# Create backup
mkdir -p "$BACKUP_DIR"

echo "Creating backup: backup-$DATE.tar.gz"
tar czf "$BACKUP_DIR/backup-$DATE.tar.gz" \
    ./data/contacts.db \
    ./data/oauth_tokens.json \
    .env.production

echo "Backup created successfully"

# Clean old backups
echo "Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup complete"
ls -lh "$BACKUP_DIR" | tail -5
```

### 6. Create Monitoring Configuration

Create `scripts/healthcheck.sh`:

```bash
#!/bin/bash

# Health check script
ENDPOINT="http://localhost:8000/health"
TIMEOUT=10

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$ENDPOINT")

if [ "$response" = "200" ]; then
    echo "OK: Application is healthy"
    exit 0
else
    echo "CRITICAL: Application returned $response"
    exit 2
fi
```

### 7. Create Deployment Documentation

Create `docs/DEPLOYMENT.md`:

```markdown
# Deployment Guide

Complete guide for deploying the Google Contacts Cisco Directory application to production.

## Prerequisites

### System Requirements
- Linux server (Ubuntu 22.04 LTS recommended)
- 2 CPU cores minimum
- 1GB RAM minimum (2GB recommended)
- 10GB disk space
- Docker 20.10+
- Docker Compose v2
- Domain name with DNS configured

### External Services
- Google Cloud Project with People API enabled
- OAuth 2.0 credentials configured
- SSL certificate (Let's Encrypt recommended)

## Initial Setup

### 1. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify installations
docker --version
docker compose version
```

### 2. Clone Repository

```bash
git clone https://github.com/your-org/google-contacts-cisco.git
cd google-contacts-cisco
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.production.example .env.production

# Edit configuration
nano .env.production

# Required settings:
# - GOOGLE_CLIENT_ID
# - GOOGLE_CLIENT_SECRET
# - OAUTH_REDIRECT_URI (https://your-domain.com/auth/callback)
# - CORS_ORIGINS (https://your-domain.com)
```

### 4. Configure SSL

```bash
# Using Let's Encrypt (recommended)
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
sudo chown $USER:$USER nginx/ssl/*
```

### 5. Deploy Application

```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh
```

## Post-Deployment

### 1. Verify Deployment

```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check health
curl https://your-domain.com/health

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 2. Configure OAuth

1. Open https://your-domain.com
2. Navigate to OAuth Setup
3. Click "Connect Google Account"
4. Authorize application
5. Verify connection successful

### 3. Initial Sync

1. Navigate to Sync Management
2. Click "Full Sync"
3. Wait for sync to complete
4. Verify contacts are available

## Maintenance

### Viewing Logs

```bash
# All logs
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f app

# Nginx access logs
tail -f logs/nginx/access.log
```

### Backups

```bash
# Manual backup
./scripts/backup.sh

# Restore from backup
tar xzf backups/backup-YYYYMMDD-HHMMSS.tar.gz
docker-compose -f docker-compose.prod.yml restart
```

### Updating Application

```bash
# Pull latest code
git pull origin main

# Redeploy
./scripts/deploy.sh
```

### Database Maintenance

```bash
# Vacuum database (optimize)
docker exec contacts-app sqlite3 /app/data/contacts.db "VACUUM;"

# Check database size
du -h ./data/contacts.db
```

## Monitoring

### Health Checks

```bash
# Application health
curl https://your-domain.com/health

# Detailed status
curl https://your-domain.com/api/sync/info
```

### Metrics

Monitor these metrics:
- Container CPU/Memory usage
- API response times
- Error rates
- Sync success/failure
- Database size

### Alerts

Set up alerts for:
- Application down (health check fails)
- High error rate (>5% of requests)
- Disk space low (<1GB free)
- SSL certificate expiring (<30 days)

## Troubleshooting

### Application Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs app

# Common issues:
# - Missing environment variables
# - Database file permissions
# - Port already in use
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Restart application
docker-compose -f docker-compose.prod.yml restart app
```

### Sync Failures

```bash
# Check OAuth status
curl https://your-domain.com/auth/status

# Check Google API access
# Verify OAuth credentials are valid
# Check API quotas in Google Cloud Console
```

## Security

### Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

## Rollback Procedure

If deployment fails:

```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Restore backup
tar xzf backups/pre-deploy-YYYYMMDD-HHMMSS.tar.gz

# Restart previous version
docker-compose -f docker-compose.prod.yml up -d
```
```

## Verification

After completing this task:

1. **Build Docker Image**:
   ```bash
   docker build -t contacts-app .
   ```

2. **Test Docker Compose**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   docker-compose -f docker-compose.prod.yml ps
   ```

3. **Test Deployment Script**:
   ```bash
   ./scripts/deploy.sh
   ```

4. **Test Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

5. **Test Backup Script**:
   ```bash
   ./scripts/backup.sh
   ls -lh backups/
   ```

## Estimated Time

4-5 hours


