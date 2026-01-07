# Configuration Guide

## Overview

The Google Contacts Cisco Directory application is configured using environment variables or a `.env` file. All settings have sensible defaults, but some (like Google OAuth credentials) must be set before the application can sync contacts.

## Architecture Note: Single-User Application

This is a **single-user application** designed to sync one Google account's contacts to Cisco IP Phones. Because of this:

- **No user sessions**: OAuth tokens are stored in a file, not cookies
- **No multi-user authentication**: Only one Google account per instance
- **Stateless APIs**: Directory and search endpoints don't require sessions
- **Simple OAuth flow**: User authenticates once, tokens persist to disk

Therefore, many security features common in multi-user web apps (session management, CSRF protection, signed cookies) are **not required**.

## Quick Start

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your Google OAuth credentials (see [Required Settings](#required-settings) below)

3. Start the application:
   ```bash
   uvicorn google_contacts_cisco.main:app --reload
   ```

## Required Settings

### Google OAuth Credentials

You **must** obtain OAuth 2.0 credentials from Google Cloud Console:

1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project or select an existing one
3. Enable the **People API**:
   - Go to APIs & Services > Library
   - Search for "People API"
   - Click Enable
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Select "Web application" as the application type
   - Add `http://localhost:8000/auth/callback` as an authorized redirect URI
   - Copy the Client ID and Client Secret

5. Set them in your `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   ```

### Secret Key (Optional)

**Note**: For this single-user application, a secret key is **optional** and only needed if you plan to implement:
- Session-based authentication in the web frontend
- Signed cookies
- CSRF protection for forms

If you don't need these features, you can skip setting the SECRET_KEY.

If you do need it later, generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set it in your `.env` file:

```env
SECRET_KEY=your_generated_secret_key_here
```

## All Configuration Options

### Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | string | "Google Contacts Cisco Directory" | Application name displayed in UI and logs |
| `DEBUG` | boolean | `false` | Enable debug mode (more verbose logging) |
| `LOG_LEVEL` | string | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `HOST` | string | `0.0.0.0` | Host address to bind the server |
| `PORT` | integer | `8000` | Port number to listen on (1-65535) |

### Database Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | `sqlite:///./data/contacts.db` | Database connection URL |
| `DATABASE_ECHO` | boolean | `false` | Log SQL queries (useful for debugging) |

### Google OAuth Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GOOGLE_CLIENT_ID` | string | (none) | **Required.** OAuth 2.0 Client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | string | (none) | **Required.** OAuth 2.0 Client Secret |
| `GOOGLE_REDIRECT_URI` | string | `http://localhost:8000/auth/callback` | OAuth callback URL (must match Google Console) |
| `GOOGLE_TOKEN_FILE` | string | `./data/token.json` | Path to store OAuth tokens |
| `GOOGLE_OAUTH_SCOPES` | list | `["https://www.googleapis.com/auth/contacts.readonly"]` | OAuth scopes to request |

### Security Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECRET_KEY` | string | (none) | Secret key for session management (optional) |

### Cisco Directory Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DIRECTORY_MAX_ENTRIES_PER_PAGE` | integer | `32` | Maximum entries per XML directory page (1-100) |
| `DIRECTORY_TITLE` | string | `"Google Contacts"` | Title displayed on Cisco phones |

### Sync Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SYNC_BATCH_SIZE` | integer | `100` | Contacts to process per sync batch (1-1000) |
| `SYNC_DELAY_SECONDS` | float | `0.1` | Delay between API requests to avoid rate limiting |

### Search Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SEARCH_RESULTS_LIMIT` | integer | `50` | Maximum search results to return (1-500) |

## Environment-Specific Configurations

### Development

Use these settings for local development:

```env
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_ECHO=true
```

### Production

Use secure settings for production:

```env
DEBUG=false
LOG_LEVEL=INFO
DATABASE_ECHO=false
HOST=0.0.0.0
PORT=8000

# Update redirect URI for your domain
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/callback
```

## Loading Configuration

Configuration is loaded automatically when the application starts. You can verify your configuration by:

### Using Python

```python
from google_contacts_cisco.config import settings
from google_contacts_cisco.config_utils import get_safe_config_dict

# Print all settings (with sensitive values masked)
print(get_safe_config_dict())
```

### Using the Health Endpoint

After starting the application, visit:
```
http://localhost:8000/health
```

This will show whether the configuration is valid and list any errors.

### Using the Configuration Summary

On startup, the application prints a configuration summary to the console:

```
Configuration Summary:
  App Name: Google Contacts Cisco Directory
  Debug: False
  Log Level: INFO
  Host: 0.0.0.0
  Port: 8000
  Database: sqlite:///./data/contacts.db
  Google Client ID: ***SET***
  Google Client Secret: ***SET***
  Redirect URI: http://localhost:8000/auth/callback
  Directory Title: Google Contacts
  Max Entries Per Page: 32
```

## Validation

The application validates configuration at startup:

1. **Required fields**: Google OAuth credentials must be set
2. **Value ranges**: Port, page sizes, and limits are validated
3. **Log levels**: Must be a valid Python logging level

If validation fails:
- In debug mode: Warnings are logged but the app continues
- In production mode: Warnings are logged; the app starts but OAuth won't work until configured

## Troubleshooting

### "GOOGLE_CLIENT_ID is not set"

You need to configure Google OAuth credentials. Follow the steps in [Required Settings](#required-settings).

### "Log level must be one of..."

Set `LOG_LEVEL` to one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### "Port must be between 1 and 65535"

Choose a valid port number. Common choices: `8000`, `8080`, `3000`

### OAuth callback errors

Make sure the `GOOGLE_REDIRECT_URI` in your `.env` file exactly matches what you configured in Google Cloud Console.

## Security Best Practices

1. **Never commit `.env`** to version control - it's already in `.gitignore`
2. **Use strong secrets** - Generate with `secrets.token_hex(32)`
3. **Restrict OAuth scopes** - Only request `contacts.readonly` unless you need write access
4. **Use HTTPS in production** - Configure a reverse proxy with SSL/TLS
5. **Protect token files** - The `data/token.json` file contains OAuth credentials

## Related Documentation

- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
- [Twelve-Factor App Config](https://12factor.net/config)
- [Google People API](https://developers.google.com/people)

