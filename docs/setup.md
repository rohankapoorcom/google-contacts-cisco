# Setup and Installation Guide

## Overview

This guide will help you set up the Google Contacts to Cisco IP Phone application from scratch. By the end of this guide, you'll have the application running locally and connected to your Google account.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Google OAuth Setup](#google-oauth-setup)
5. [First Sync](#first-sync)
6. [Verification](#verification)
7. [Next Steps](#next-steps)

---

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Python**: 3.10 or higher
- **RAM**: 2GB minimum (4GB recommended)
- **Disk Space**: 500MB minimum
- **Network**: Internet connection for Google API access

### Required Software

1. **Python 3.10+**
   ```bash
   python3 --version
   # Should output: Python 3.10.x or higher
   ```

2. **pip** (Python package manager)
   ```bash
   pip3 --version
   ```

3. **uv** (recommended) or **virtualenv**
   ```bash
   pip3 install uv
   ```

### Optional Tools

- **Docker** and **Docker Compose** (for containerized deployment)
- **Git** (for version control)
- **curl** or **Postman** (for API testing)

---

## Installation

### Option 1: Using Dev Container (Recommended for Development)

The project includes a pre-configured development container that provides a consistent development environment.

#### Requirements
- Docker Desktop
- VS Code or Cursor with Dev Containers extension

#### Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd google-contacts-cisco
   ```

2. **Open in Container**
   - Open the project in VS Code/Cursor
   - When prompted, click "Reopen in Container"
   - Or use Command Palette: "Dev Containers: Reopen in Container"

3. **Wait for Setup**
   The container will automatically:
   - Set up Python 3.13 environment
   - Install all dependencies
   - Configure development tools

4. **Verify Installation**
   ```bash
   python --version
   uv --version
   ```

### Option 2: Local Installation with uv

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd google-contacts-cisco
   ```

2. **Install uv**
   ```bash
   pip install uv
   ```

3. **Create Virtual Environment and Install Dependencies**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

4. **Verify Installation**
   ```bash
   python -c "import google_contacts_cisco; print(google_contacts_cisco.__version__)"
   ```

### Option 3: Traditional Installation with pip

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd google-contacts-cisco
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Upgrade pip**
   ```bash
   pip install --upgrade pip
   ```

4. **Install Dependencies**
   ```bash
   pip install -e .
   ```

5. **Verify Installation**
   ```bash
   python -c "import google_contacts_cisco; print(google_contacts_cisco.__version__)"
   ```

---

## Configuration

### 1. Create Configuration File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Edit Configuration

Open `.env` in your favorite text editor:

```bash
nano .env  # or vim, code, etc.
```

### 3. Required Settings

#### Database Configuration

```env
# Database location
DATABASE_URL=sqlite:///./data/contacts.db
```

The application will create the `data` directory automatically.

#### Google OAuth Credentials

You'll set these up in the next section. For now, leave them as placeholders:

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

#### Application Settings

```env
# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Logging
LOG_LEVEL=INFO

# Sync scheduler (optional)
SYNC_SCHEDULER_ENABLED=false
SYNC_INTERVAL_MINUTES=30
```

### 4. Configuration Options Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | SQLite database path | `sqlite:///./data/contacts.db` | Yes |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID | - | Yes |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret | - | Yes |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL | `http://localhost:8000/auth/callback` | Yes |
| `HOST` | Server bind address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `DEBUG` | Debug mode | `false` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `SYNC_SCHEDULER_ENABLED` | Auto-sync scheduler | `false` | No |
| `SYNC_INTERVAL_MINUTES` | Sync interval | `30` | No |
| `TOKEN_FILE` | OAuth token storage | `./data/token.json` | No |

### 5. Initialize Database

Run database migrations:

```bash
uv run alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 3b6d750552da, initial_schema
```

---

## Google OAuth Setup

To access Google Contacts, you need to create OAuth 2.0 credentials in the Google Cloud Console.

### Step 1: Create a Google Cloud Project

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create New Project**
   - Click "Select a project" → "New Project"
   - Project name: `Google Contacts Cisco` (or your choice)
   - Click "Create"

3. **Wait for Project Creation**
   - This usually takes 10-30 seconds

### Step 2: Enable Google People API

1. **Navigate to APIs & Services**
   - From the sidebar: "APIs & Services" → "Library"

2. **Search for People API**
   - Search box: "Google People API"
   - Click on "Google People API"

3. **Enable the API**
   - Click "Enable"
   - Wait for confirmation

### Step 3: Create OAuth Consent Screen

1. **Navigate to OAuth Consent Screen**
   - Sidebar: "APIs & Services" → "OAuth consent screen"

2. **Choose User Type**
   - Select "External" (unless you have a Google Workspace domain)
   - Click "Create"

3. **Fill App Information**
   - **App name**: `Google Contacts Sync`
   - **User support email**: Your email
   - **Developer contact**: Your email
   - Leave other fields as default
   - Click "Save and Continue"

4. **Scopes Configuration**
   - Click "Add or Remove Scopes"
   - Search for: `https://www.googleapis.com/auth/contacts.readonly`
   - Check the box next to it
   - Click "Update"
   - Click "Save and Continue"

5. **Test Users** (if app is in testing mode)
   - Click "Add Users"
   - Enter your Gmail address
   - Click "Add"
   - Click "Save and Continue"

6. **Summary**
   - Review settings
   - Click "Back to Dashboard"

### Step 4: Create OAuth Credentials

1. **Navigate to Credentials**
   - Sidebar: "APIs & Services" → "Credentials"

2. **Create Credentials**
   - Click "Create Credentials" → "OAuth client ID"

3. **Application Type**
   - **Application type**: Web application
   - **Name**: `Google Contacts Cisco OAuth`

4. **Authorized Redirect URIs**
   - Click "Add URI"
   - Enter: `http://localhost:8000/auth/callback`
   - For production, add your production URL: `https://yourdomain.com/auth/callback`
   - Click "Create"

5. **Save Credentials**
   - A dialog will show your Client ID and Client Secret
   - **IMPORTANT**: Copy these values - you won't see them again!
   - Click "OK"

### Step 5: Update Configuration

1. **Edit `.env` File**
   ```bash
   nano .env
   ```

2. **Paste Your Credentials**
   ```env
   GOOGLE_CLIENT_ID=1234567890-abcdef.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456ghi789
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
   ```

3. **Save and Close**
   - Press `Ctrl+X`, then `Y`, then `Enter` (in nano)

### Step 6: Verify Configuration

```bash
uv run python -m google_contacts_cisco.config_utils
```

You should see:
```
✓ Google OAuth credentials configured
✓ Database configured
✓ Configuration valid
```

---

## Starting the Application

### Development Mode

Start the application in development mode with auto-reload:

```bash
# Using uv (recommended)
uv run uvicorn google_contacts_cisco.main:app --reload --host 0.0.0.0 --port 8000

# Or using the dev script
./scripts/dev.sh
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Production Mode

For production, use Gunicorn with Uvicorn workers:

```bash
uv run gunicorn google_contacts_cisco.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker (Optional)

If you prefer Docker:

```bash
# Build image
docker build -t google-contacts-cisco .

# Run container
docker run -d \
  --name google-contacts-cisco \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env \
  google-contacts-cisco
```

---

## First Sync

### 1. Open Application

Visit http://localhost:8000 in your browser.

### 2. Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "debug": true,
  "config_valid": true,
  "config_errors": []
}
```

### 3. Authenticate with Google

#### Option A: Using Browser

1. Visit: http://localhost:8000/auth/google
2. Sign in with your Google account
3. Grant permissions to access contacts (read-only)
4. You'll be redirected back with a success message

#### Option B: Using API

```bash
# Get OAuth URL
curl http://localhost:8000/auth/url

# Copy the "auth_url" from response and open in browser
# Complete OAuth flow
```

### 4. Verify Authentication

```bash
curl http://localhost:8000/auth/status
```

Expected response:
```json
{
  "authenticated": true,
  "has_token_file": true,
  "credentials_valid": true,
  "credentials_expired": false,
  "has_refresh_token": true,
  "scopes": [
    "https://www.googleapis.com/auth/contacts.readonly"
  ]
}
```

### 5. Test Google Connection

```bash
curl http://localhost:8000/api/test-connection
```

Expected response:
```json
{
  "status": "success",
  "message": "Successfully connected to Google People API",
  "total_contacts": 150
}
```

### 6. Perform Initial Sync

```bash
curl -X POST http://localhost:8000/api/sync
```

This will download all contacts from Google. Depending on the number of contacts, this can take:
- < 1000 contacts: 5-15 seconds
- 1000-5000 contacts: 15-60 seconds  
- 5000+ contacts: 1-5 minutes

Expected response:
```json
{
  "status": "success",
  "message": "Full sync completed successfully",
  "statistics": {
    "sync_type": "full",
    "contacts_added": 150,
    "contacts_updated": 0,
    "contacts_deleted": 0,
    "total_contacts": 150,
    "duration_seconds": 12.34,
    "started_at": "2026-01-08T10:30:00Z",
    "completed_at": "2026-01-08T10:30:12Z"
  }
}
```

### 7. View Contacts

```bash
curl http://localhost:8000/api/contacts?limit=10
```

---

## Verification

### Check All Components

Run this verification script to ensure everything is working:

```bash
#!/bin/bash

echo "=== Google Contacts Cisco - Verification ==="
echo ""

echo "1. Health Check"
curl -s http://localhost:8000/health | jq .
echo ""

echo "2. Authentication Status"
curl -s http://localhost:8000/auth/status | jq .
echo ""

echo "3. Sync Status"
curl -s http://localhost:8000/api/sync/status | jq .
echo ""

echo "4. Contact Count"
curl -s http://localhost:8000/api/contacts/stats | jq .
echo ""

echo "5. Sample Contacts"
curl -s http://localhost:8000/api/contacts?limit=3 | jq '.contacts[] | {display_name, phone_numbers}'
echo ""

echo "=== Verification Complete ==="
```

Save as `verify.sh`, make executable, and run:

```bash
chmod +x verify.sh
./verify.sh
```

### Expected Output

All checks should pass:
- ✓ Health check returns "healthy"
- ✓ Authentication status shows "authenticated": true
- ✓ Sync status shows last sync time
- ✓ Contact stats show your contact count
- ✓ Sample contacts display correctly

---

## Troubleshooting

### Common Issues

#### Port Already in Use

**Error**: `Address already in use`

**Solution**: Change port in `.env`:
```env
PORT=8001
```

Or stop the conflicting process:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### OAuth Configuration Not Found

**Error**: `Google OAuth credentials not configured`

**Solution**: 
1. Check `.env` file has correct credentials
2. Verify no extra spaces in values
3. Restart application after updating `.env`

#### Database Migration Failed

**Error**: `alembic.util.exc.CommandError`

**Solution**:
```bash
# Remove existing database
rm data/contacts.db

# Re-run migrations
uv run alembic upgrade head
```

#### Google API Connection Failed

**Error**: `Connection test failed`

**Solution**:
1. Check internet connection
2. Verify Google People API is enabled in Cloud Console
3. Check OAuth credentials are correct
4. Try refreshing token: `curl -X POST http://localhost:8000/auth/refresh`

#### Token Expired

**Error**: `Token refresh failed: invalid_grant`

**Solution**:
```bash
# Revoke old credentials
curl -X POST http://localhost:8000/auth/revoke

# Re-authenticate
# Visit: http://localhost:8000/auth/google
```

For more detailed troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).

---

## Next Steps

Now that you have the application running, you can:

1. **Set Up Frontend** (Optional)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. **Configure Cisco IP Phones**
   - See [Cisco Phone Setup Guide](cisco-phone-setup.md)

3. **Set Up Scheduled Sync**
   - Enable in `.env`:
   ```env
   SYNC_SCHEDULER_ENABLED=true
   SYNC_INTERVAL_MINUTES=30
   ```

4. **Deploy to Production**
   - See [Deployment Guide](deployment.md)

5. **Explore API**
   - Interactive docs: http://localhost:8000/docs
   - API reference: [API Documentation](api.md)

---

## Security Recommendations

### Development

1. **Keep credentials secure**
   - Never commit `.env` file to version control
   - Add to `.gitignore`

2. **Use separate Google project for development**
   - Create separate OAuth credentials for dev/prod

3. **Limit test user access**
   - Only add necessary test users in Google Console

### Production

1. **Use HTTPS**
   - Set up SSL/TLS certificates
   - Update redirect URI to use HTTPS

2. **Restrict CORS**
   - Disable or restrict CORS in production
   - Use reverse proxy for CORS handling

3. **Secure token storage**
   - Use appropriate file permissions:
   ```bash
   chmod 600 data/token.json
   ```

4. **Regular updates**
   - Keep dependencies updated
   - Monitor security advisories

5. **Backup database**
   - Regular backups of `data/contacts.db`
   - Test restore procedures

---

## Getting Help

### Documentation

- **API Reference**: [api.md](api.md)
- **Authentication Guide**: [authentication.md](authentication.md)
- **Deployment Guide**: [deployment.md](deployment.md)
- **Troubleshooting**: [troubleshooting.md](troubleshooting.md)

### Interactive Tools

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Logs

Check application logs for detailed error messages:

```bash
# In development
# Logs are printed to console

# In production
tail -f /var/log/google-contacts-cisco/app.log
```

### Support

For issues and questions:
1. Check [Troubleshooting Guide](troubleshooting.md)
2. Review application logs
3. Check Google Cloud Console for API errors
4. Verify network connectivity

---

## Conclusion

You should now have a fully functional Google Contacts to Cisco IP Phone application running locally. The application is ready to:

- Sync contacts from Google
- Serve contacts via REST API
- Provide Cisco XML directory for IP phones
- Support real-time contact search

For production deployment, see the [Deployment Guide](deployment.md).
