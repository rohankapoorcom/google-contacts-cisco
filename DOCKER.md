# Docker Deployment Guide

This document provides instructions for deploying the Google Contacts Cisco Directory application using Docker and Docker Compose.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Building the Image](#building-the-image)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Using Pre-built Images](#using-pre-built-images)
- [Management](#management)
- [Reverse Proxy Configuration](#reverse-proxy-configuration)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

## Quick Start

### Development

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with your Google OAuth credentials

# 2. Build and start
docker-compose up -d

# 3. Access application
open http://localhost:8000
```

### Production

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with production settings (DEBUG=false, etc.)

# 2. Build and start
docker-compose -f docker-compose.prod.yml up -d

# 3. Configure your reverse proxy to point to port 8000
```

## Prerequisites

- **Docker Engine**: 20.10 or later
- **Docker Compose**: 2.0 or later (or `docker compose` plugin)
- **System Requirements**:
  - 2GB RAM minimum (4GB recommended)
  - 10GB disk space
  - Linux, macOS, or Windows with WSL2

### Installation

#### Ubuntu/Debian
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

#### macOS
```bash
# Install Docker Desktop
brew install --cask docker
```

#### Windows
Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

## Configuration

### Environment Variables

**Important**: A `.env` file is required before running the Docker containers. The Docker Compose configurations mount this file as a read-only volume.

Copy `.env.example` to `.env` and configure:

```bash
# Application
APP_NAME="Google Contacts Cisco Directory"
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/contacts.db

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/callback
GOOGLE_TOKEN_FILE=./data/token.json

# Cisco Directory
DIRECTORY_MAX_ENTRIES_PER_PAGE=32
DIRECTORY_TITLE="Google Contacts"

# Sync
SYNC_BATCH_SIZE=100
SYNC_DELAY_SECONDS=0.1
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **Google People API**
4. Create OAuth 2.0 credentials (Web application type)
5. Add authorized redirect URI: `https://your-domain.com/auth/callback`
6. Copy Client ID and Client Secret to `.env`

## Building the Image

### Build Locally

```bash
# Build the image
docker build -t google-contacts-cisco .

# Or using docker-compose
docker-compose build
```

The build process:
1. Builds the Vue.js frontend (Node.js 18)
2. Installs Python dependencies using uv
3. Creates optimized production image
4. Total build time: ~5-10 minutes

### Multi-platform Builds

Pre-built images from GitHub Container Registry support both `linux/amd64` and `linux/arm64` architectures automatically.

To build locally for multiple platforms:

```bash
# Set up buildx (one-time setup)
docker buildx create --use

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t google-contacts-cisco .
```

## Development Deployment

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Hot Reloading

The development configuration mounts source code as volumes, enabling hot reloading:

```bash
# Edit code - changes are reflected immediately
# No need to rebuild container for Python changes
```

### Frontend Development

For frontend development with Vite's hot module replacement:

```bash
# Terminal 1: Run backend in Docker
docker-compose up

# Terminal 2: Run frontend dev server
cd frontend
npm install
npm run dev
```

Access frontend at `http://localhost:5173` with API proxy to Docker backend.

## Production Deployment

### Using Docker Compose

```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Configuration Best Practices

1. **Use environment file**:
   ```bash
   # Set permissions
   chmod 600 .env
   ```

2. **Configure resource limits** in `docker-compose.prod.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 1G
   ```

3. **Set up persistent volumes**:
   - Database: `/app/data`
   - Logs: `/app/logs`

4. **Configure health checks**:
   - Health endpoint: `http://localhost:8000/health`
   - Interval: 30 seconds
   - Retries: 3

## Using Pre-built Images

Pre-built Docker images are automatically published via GitHub Actions and available on GitHub Container Registry (ghcr.io).

### Pull and Run

```bash
# Pull latest image (main branch)
docker pull ghcr.io/rohankapoorcom/google-contacts-cisco:main

# Run container
docker run -d \
  --name google-contacts-cisco \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  --restart unless-stopped \
  ghcr.io/rohankapoorcom/google-contacts-cisco:main
```

### Available Tags

Images are automatically published to GitHub Container Registry with the following tags:

- `main` - Latest commit from main branch
- `0.1.0` - Specific version (auto-bumped on each push to main)
- `pr-123-0.1.0` - Pull request builds with version
- `pr-123-sha` - Pull request builds with commit SHA

**Note**: Version numbers are automatically incremented on every push to main using [bump-my-version](https://github.com/callowayproject/bump-my-version).

### Using with Docker Compose

```yaml
services:
  app:
    image: ghcr.io/rohankapoorcom/google-contacts-cisco:main
    # ... rest of configuration
```

## Management

### Service Operations

```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Stop services
docker-compose -f docker-compose.prod.yml stop

# Restart services
docker-compose -f docker-compose.prod.yml restart

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Execute commands in container
docker-compose -f docker-compose.prod.yml exec app bash

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### Database Operations

```bash
# Access database
docker-compose -f docker-compose.prod.yml exec app sqlite3 /app/data/contacts.db

# Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Create migration
docker-compose -f docker-compose.prod.yml exec app alembic revision --autogenerate -m "Description"

# View migration history
docker-compose -f docker-compose.prod.yml exec app alembic history
```

### Backup and Restore

#### Manual Backup

```bash
# Stop application
docker-compose -f docker-compose.prod.yml stop app

# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Start application
docker-compose -f docker-compose.prod.yml start app
```

#### Automated Backups

Set up a cron job or systemd timer for regular backups:

```bash
# Example cron job (daily at 2 AM)
0 2 * * * cd /path/to/app && tar -czf backups/backup-$(date +\%Y\%m\%d).tar.gz data/
```

#### Restore

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore data
tar -xzf backup-20260109.tar.gz

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Or using pre-built images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

## Reverse Proxy Configuration

The application runs on port 8000 and should be placed behind a reverse proxy for production use. Here are example configurations for popular proxies.

### Nginx

```nginx
server {
    listen 80;
    server_name contacts.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Caddy

```caddy
contacts.yourdomain.com {
    reverse_proxy localhost:8000
}
```

### Traefik (Docker Labels)

```yaml
services:
  app:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.contacts.rule=Host(`contacts.yourdomain.com`)"
      - "traefik.http.routers.contacts.entrypoints=websecure"
      - "traefik.http.routers.contacts.tls.certresolver=letsencrypt"
```

### Nginx Proxy Manager

1. Add a new proxy host
2. Domain: `contacts.yourdomain.com`
3. Forward Hostname/IP: `app` (or `localhost`)
4. Forward Port: `8000`
5. Enable SSL with Let's Encrypt

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs app

# Check configuration
docker-compose -f docker-compose.prod.yml config

# Rebuild from scratch
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Health Check Failures

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check container health
docker-compose -f docker-compose.prod.yml ps

# View detailed logs
docker-compose -f docker-compose.prod.yml logs --tail=100 app
```

### Database Issues

```bash
# Check database file
docker-compose -f docker-compose.prod.yml exec app ls -la /app/data/

# Check database integrity
docker-compose -f docker-compose.prod.yml exec app sqlite3 /app/data/contacts.db "PRAGMA integrity_check;"

# Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Permission Issues

```bash
# Fix data directory permissions (container runs as UID 1000)
sudo chown -R 1000:1000 data/
chmod 755 data/
chmod 644 data/contacts.db
chmod 600 data/token.json
```

### Out of Memory

```bash
# Check container resource usage
docker stats

# Increase memory limits in docker-compose.prod.yml
# Under deploy.resources.limits.memory
```

### Frontend Not Loading

```bash
# Verify frontend was built
docker-compose -f docker-compose.prod.yml exec app ls -la /app/google_contacts_cisco/static/dist/

# Rebuild with frontend
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## Security

### Best Practices

1. **Run as Non-Root**
   - ✅ Container runs as user `appuser` (UID 1000)
   - ✅ Capabilities dropped in production

2. **Secrets Management**
   - ✅ Use `.env` file with restricted permissions (`chmod 600 .env`)
   - ✅ Never commit secrets to git
   - Consider using Docker secrets or external secret managers

3. **Network Security**
   - ✅ Use reverse proxy (nginx, Caddy, Traefik, etc.)
   - ✅ Enable HTTPS/SSL at proxy level
   - ✅ Configure firewall to only allow proxy access

4. **Updates**
   - Regularly update base images
   - Monitor security advisories
   - Use automated dependency updates

5. **Monitoring**
   - Check logs regularly
   - Monitor resource usage
   - Set up health check alerts

### Security Checklist

- [ ] `.env` file has secure permissions (600)
- [ ] HTTPS enabled at reverse proxy
- [ ] Reverse proxy configured with security headers
- [ ] Firewall configured (only reverse proxy can access port 8000)
- [ ] Regular backups scheduled
- [ ] Log monitoring enabled
- [ ] Resource limits configured
- [ ] Updates applied regularly

## Additional Resources

- [Main Documentation](README.md)
- [API Documentation](docs/api.md)
- [Full Deployment Guide](docs/deployment.md)
- [Troubleshooting Guide](docs/troubleshooting.md)
- [Docker Documentation](https://docs.docker.com)
- [Docker Compose Documentation](https://docs.docker.com/compose)

## Support

For issues and questions:
- Check [Troubleshooting](docs/troubleshooting.md)
- Review application logs
- Check GitHub issues
- Review Docker logs: `docker-compose logs`

## License

MIT License - See [LICENSE](LICENSE) for details
