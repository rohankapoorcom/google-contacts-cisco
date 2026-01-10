# Google Contacts to Cisco IP Phone

A comprehensive web application that synchronizes Google Contacts and serves them to Cisco IP Phones via XML directory service, with a modern web interface for management.

## Features

- 🔐 **OAuth 2.0 Authentication**: Secure integration with Google Contacts API
- 🔄 **Automatic Synchronization**: Full and incremental sync with scheduling support
- 📡 **REST API**: Complete API for contact management, search, and sync operations
- 📞 **Cisco XML Directory**: Three-level hierarchy optimized for Cisco IP Phones
- 🔍 **Full-Text Search**: Fast contact search by name and phone number
- 🎨 **Modern Frontend**: Vue 3 + TypeScript web interface
- 📊 **Sync Management**: Real-time status, statistics, and history tracking
- 🐳 **Docker Support**: Pre-built images published via GitHub Actions
- 🚀 **Production Ready**: Systemd service, reverse proxy support

## Quick Start

### Prerequisites

- Python 3.10+
- Google Cloud Project with People API enabled
- OAuth 2.0 credentials
- 2GB RAM minimum (see [Memory Requirements](#memory-requirements))

### Memory Requirements

The application manages memory efficiently during synchronization:

- **Small Lists (< 1K contacts)**: 512MB minimum
- **Medium Lists (1K-5K contacts)**: 1-2GB recommended  
- **Large Lists (5K-10K contacts)**: 2-4GB recommended
- **Very Large Lists (10K+ contacts)**: 4GB+ recommended

The sync service automatically clears SQLAlchemy's session cache after each batch to prevent memory leaks. Optional memory monitoring is available with `psutil` installed.

### Installation

```bash
# Clone repository
git clone https://github.com/rohankapoorcom/google-contacts-cisco.git
cd google-contacts-cisco

# Install dependencies
pip install uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your Google OAuth credentials

# Run database migrations
uv run alembic upgrade head

# Start application
uv run uvicorn google_contacts_cisco.main:app --reload
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

### Getting Started
- **[Setup Guide](docs/setup.md)** - Complete installation and configuration instructions
- **[Authentication Guide](docs/authentication.md)** - OAuth 2.0 setup and token management

### User Guides
- **[Cisco Phone Setup](docs/cisco-phone-setup.md)** - Configure Cisco IP Phones to use the directory
- **[API Documentation](docs/api.md)** - Complete API reference with examples
- **[Postman Collection](docs/postman/)** - Ready-to-use API testing collection

### Operations
- **[Deployment Guide](docs/deployment.md)** - Production deployment with Docker, systemd, nginx
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions

### Development
- **[Configuration Guide](docs/configuration.md)** - Configuration options and best practices
- **[Testing Guide](docs/testing.md)** - Testing strategy and coverage requirements

## API Endpoints

### Authentication
- `GET /auth/url` - Get OAuth authorization URL
- `GET /auth/google` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/status` - Check authentication status
- `POST /auth/refresh` - Refresh access token
- `POST /auth/revoke` - Revoke credentials

### Contacts
- `GET /api/contacts` - List contacts with pagination
- `GET /api/contacts/{id}` - Get single contact
- `GET /api/contacts/stats` - Get contact statistics
- `GET /api/search` - Search contacts by name or phone

### Synchronization
- `POST /api/sync` - Trigger auto sync (full or incremental)
- `POST /api/sync/full` - Force full synchronization
- `POST /api/sync/incremental` - Incremental sync
- `GET /api/sync/status` - Get sync status
- `GET /api/sync/statistics` - Get comprehensive statistics

### Cisco Directory (XML)
- `GET /directory` - Main directory menu
- `GET /directory/groups/{group}` - Group directory
- `GET /directory/contacts/{id}` - Contact directory

For detailed API documentation, visit:
- **Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **Alternative Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)
- **Full API Guide**: [docs/api.md](docs/api.md)

## Development Setup

### Using Dev Container (Recommended)

This project includes a pre-configured development container:

1. Open in VS Code/Cursor
2. Click "Reopen in Container" when prompted
3. Container automatically sets up Python 3.13 and all dependencies

The devcontainer includes:
- Python 3.13 environment
- All project dependencies
- Development tools (Black, mypy, pytest)
- Pre-configured VS Code extensions

### Local Development

```bash
# Format code
black .

# Type checking
mypy .

# Run tests
pytest

# Run tests with coverage
pytest --cov=google_contacts_cisco --cov-report=html

# Run development server
./scripts/dev.sh
```

## Deployment

### Docker

Pre-built Docker images are automatically published via GitHub Actions and available on GitHub Container Registry.

#### Using Pre-built Images

```bash
# Pull latest image (main branch)
docker pull ghcr.io/rohankapoorcom/google-contacts-cisco:main

# Or pull a specific version
docker pull ghcr.io/rohankapoorcom/google-contacts-cisco:0.1.0

# Run with docker-compose
# Update docker-compose.prod.yml to use: image: ghcr.io/rohankapoorcom/google-contacts-cisco:main
docker-compose -f docker-compose.prod.yml up -d
```

**Note**: Version numbers are automatically bumped on every push to main. Images are tagged with both the branch name (`main`) and the version number (e.g., `0.1.0`).

#### Building Locally

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

See [DOCKER.md](DOCKER.md) for comprehensive Docker deployment guide including:
- Configuration options
- Reverse proxy setup (nginx, Caddy, Traefik)
- Backup and restore procedures
- Troubleshooting

### Systemd Service

See [Deployment Guide](docs/deployment.md) for complete systemd service setup and production configuration.

## Configuration

Configuration is managed through environment variables in `.env` file:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Database
DATABASE_URL=sqlite:///./data/contacts.db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Sync Scheduler (Optional)
SYNC_SCHEDULER_ENABLED=true
SYNC_INTERVAL_MINUTES=30

# Reverse Proxy (Required if behind nginx, Traefik, etc.)
# JSON array of trusted proxy IPs/CIDR ranges
TRUSTED_PROXIES=["127.0.0.1", "172.17.0.0/16"]
```

**Important**: If deploying behind a reverse proxy with HTTPS termination (nginx, Traefik, Apache, etc.), you **must** set `TRUSTED_PROXIES` to your proxy's IP address for OAuth to work correctly. See [Reverse Proxy Setup Guide](docs/reverse-proxy-setup.md) for details.

See [Configuration Guide](docs/configuration.md) for all available options.

## Architecture

```plaintext
┌─────────────────┐
│  Vue 3 Frontend │ ← User interface
└────────┬────────┘
         │
    ┌────▼────────┐
    │  FastAPI    │ ← REST API
    │  Backend    │
    └────┬────────┘
         │
    ┌────▼─────────┐
    │   SQLite     │ ← Local database
    │   Database   │
    └──────────────┘
         │
    ┌────▼──────────────┐
    │  Google Contacts  │ ← Google People API
    │      API          │
    └───────────────────┘
         │
    ┌────▼──────────────┐
    │  Cisco IP Phones  │ ← XML directory
    └───────────────────┘
```

## Technology Stack

- **Backend**: FastAPI, Python 3.10+
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Vue 3, TypeScript, Tailwind CSS
- **Authentication**: Google OAuth 2.0
- **API Integration**: Google People API
- **Phone Integration**: Cisco IP Phone XML Objects

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=google_contacts_cisco

# Run specific test file
pytest tests/unit/api/test_contacts.py

# Run with verbose output
pytest -v
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

Common issues and solutions:

- **OAuth "insecure_transport" error**: If behind a reverse proxy, set `BEHIND_PROXY=true` in `.env`. See [Reverse Proxy Setup Guide](docs/reverse-proxy-setup.md)
- **OAuth not working**: Check credentials in `.env` and redirect URI in Google Console
- **Sync fails**: Verify authentication with `GET /auth/status`
- **No contacts**: Trigger sync with `POST /api/sync`
- **Phone can't access directory**: Check network connectivity and firewall rules

See [Troubleshooting Guide](docs/troubleshooting.md) for detailed solutions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Documentation**: [docs/](docs/)
- **API Reference**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Troubleshooting**: [docs/troubleshooting.md](docs/troubleshooting.md)

## Acknowledgments

- Google People API for contact synchronization
- Cisco IP Phone XML Objects for directory integration
- FastAPI for the excellent API framework
- Vue 3 for the modern frontend framework

