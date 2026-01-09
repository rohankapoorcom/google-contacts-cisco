# Authentication Guide

## Overview

The Google Contacts to Cisco IP Phone application uses OAuth 2.0 for authenticating with Google's People API. This guide provides detailed information about the authentication flow, token management, and troubleshooting authentication issues.

## Table of Contents

1. [OAuth 2.0 Flow](#oauth-20-flow)
2. [Token Management](#token-management)
3. [API Endpoints](#api-endpoints)
4. [Implementation Details](#implementation-details)
5. [Security Considerations](#security-considerations)
6. [Troubleshooting](#troubleshooting)

---

## OAuth 2.0 Flow

### Overview

OAuth 2.0 is an authorization framework that enables applications to obtain limited access to user accounts on an HTTP service. In our case, we use OAuth 2.0 to access Google Contacts data with the user's permission.

### Flow Diagram

```plaintext
┌─────────┐                                           ┌───────────┐
│         │  1. Initiate OAuth (GET /auth/google)   │           │
│  User   │──────────────────────────────────────────>│    App    │
│         │                                           │           │
└─────────┘                                           └───────────┘
     │                                                       │
     │                                                       │ 2. Redirect
     │                                                       │ to Google
     │                                                       ▼
     │                                              ┌──────────────┐
     │    3. Sign in and                            │              │
     │    grant permissions                         │   Google     │
     └─────────────────────────────────────────────>│   OAuth      │
                                                    │              │
                                                    └──────────────┘
                                                           │
                                                           │ 4. Callback
                                                           │ with code
                                                           ▼
┌─────────┐                                           ┌───────────┐
│         │    5. Exchange code for tokens           │           │
│  User   │<──────────────────────────────────────────│    App    │
│         │    6. Success page                        │           │
└─────────┘                                           └───────────┘
```

### Step-by-Step Process

#### Step 1: Initiate OAuth Flow

The user clicks "Connect Google Account" or visits `/auth/google`:

**Request**:
```http
GET /auth/google HTTP/1.1
Host: localhost:8000
```

**Response**:
```http
HTTP/1.1 307 Temporary Redirect
Location: https://accounts.google.com/o/oauth2/v2/auth?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=http://localhost:8000/auth/callback&
  scope=https://www.googleapis.com/auth/contacts.readonly&
  access_type=offline&
  response_type=code&
  state=RANDOM_STATE
```

#### Step 2: User Authentication

The user is redirected to Google's consent screen where they:
1. Sign in with their Google account (if not already signed in)
2. Review the permissions requested (read-only access to contacts)
3. Click "Allow" to grant permissions

#### Step 3: Authorization Code

Google redirects back to the application with an authorization code:

```
http://localhost:8000/auth/callback?
  code=4/0AfJohX...&
  state=RANDOM_STATE&
  scope=https://www.googleapis.com/auth/contacts.readonly
```

#### Step 4: Token Exchange

The application exchanges the authorization code for access and refresh tokens:

**Request to Google**:
```http
POST https://oauth2.googleapis.com/token
Content-Type: application/x-www-form-urlencoded

code=4/0AfJohX...&
client_id=YOUR_CLIENT_ID&
client_secret=YOUR_CLIENT_SECRET&
redirect_uri=http://localhost:8000/auth/callback&
grant_type=authorization_code
```

**Response from Google**:
```json
{
  "access_token": "ya29.a0AfH6SM...",
  "expires_in": 3599,
  "refresh_token": "1//0gQ-Xt...",
  "scope": "https://www.googleapis.com/auth/contacts.readonly",
  "token_type": "Bearer"
}
```

#### Step 5: Token Storage

The application securely stores the tokens in `data/token.json`:

```json
{
  "token": "ya29.a0AfH6SM...",
  "refresh_token": "1//0gQ-Xt...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
  "client_secret": "YOUR_CLIENT_SECRET",
  "scopes": ["https://www.googleapis.com/auth/contacts.readonly"],
  "expiry": "2026-01-08T11:30:00.000000Z"
}
```

#### Step 6: Success

The user sees a success page and can now use the application.

---

## Token Management

### Token Types

#### Access Token
- **Purpose**: Authenticate API requests to Google
- **Lifetime**: 1 hour (3600 seconds)
- **Usage**: Included in API requests as Bearer token
- **Format**: JWT (JSON Web Token)

Example:
```
Authorization: Bearer ya29.a0AfH6SMBuWv...
```

#### Refresh Token
- **Purpose**: Obtain new access tokens without user interaction
- **Lifetime**: Indefinite (until revoked)
- **Usage**: Automatically used when access token expires
- **Security**: Never sent in API requests, stored securely

### Automatic Token Refresh

The application automatically refreshes access tokens when they expire:

1. **Detection**: Before each API call, check if token is expired
2. **Refresh**: Use refresh token to get new access token
3. **Storage**: Save new access token and expiry time
4. **Retry**: Retry original API request with new token

**Code Flow**:
```python
# Pseudo-code
if credentials.expired and credentials.refresh_token:
    credentials.refresh(Request())
    save_credentials(credentials)
```

### Manual Token Refresh

You can manually refresh tokens via API:

```bash
curl -X POST http://localhost:8000/auth/refresh
```

Response:
```json
{
  "success": true,
  "message": "Access token refreshed successfully"
}
```

### Token Revocation

To revoke access and delete tokens:

```bash
curl -X POST http://localhost:8000/auth/revoke
```

This will:
1. Call Google's revoke endpoint
2. Delete local `token.json` file
3. Clear in-memory credentials

---

## API Endpoints

### GET /auth/url

Get OAuth URL for client-side redirect.

**Use Case**: Frontend applications that want to handle the redirect themselves.

**Request**:
```bash
curl http://localhost:8000/auth/url
```

**Response**:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": null
}
```

**With Custom Redirect**:
```bash
curl "http://localhost:8000/auth/url?redirect_uri=/sync"
```

Response includes state with redirect URI:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "/sync"
}
```

### GET /auth/google

Server-side OAuth initiation (redirect).

**Use Case**: Direct browser access or server-initiated OAuth flow.

**Request**:
```
http://localhost:8000/auth/google
```

**Response**: 307 Temporary Redirect to Google OAuth

### GET /auth/callback

OAuth callback handler.

**Use Case**: Automatic callback from Google after user grants permissions.

**Parameters** (provided by Google):
- `code`: Authorization code
- `state`: State parameter (may contain redirect URI)
- `error`: Error code if user denied access

**Response**: HTML success or error page

### GET /auth/status

Check authentication status.

**Request**:
```bash
curl http://localhost:8000/auth/status
```

**Response**:
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

**Status Fields**:

| Field | Description |
|-------|-------------|
| `authenticated` | Overall authentication state (true if can make API calls) |
| `has_token_file` | Token file exists on disk |
| `credentials_valid` | Credentials are valid and not expired |
| `credentials_expired` | Access token has expired (but may be refreshable) |
| `has_refresh_token` | Refresh token is available for renewal |
| `scopes` | OAuth scopes granted by user |

**Interpretation**:

✅ **Fully Authenticated**:
```json
{
  "authenticated": true,
  "credentials_valid": true,
  "credentials_expired": false,
  "has_refresh_token": true
}
```

⚠️ **Expired but Renewable**:
```json
{
  "authenticated": true,
  "credentials_valid": false,
  "credentials_expired": true,
  "has_refresh_token": true
}
```
Action: Automatic refresh will happen on next API call, or manually call `/auth/refresh`

❌ **Not Authenticated**:
```json
{
  "authenticated": false,
  "has_token_file": false
}
```
Action: Complete OAuth flow via `/auth/google`

❌ **Authentication Failed**:
```json
{
  "authenticated": false,
  "credentials_expired": true,
  "has_refresh_token": false
}
```
Action: Re-authenticate via `/auth/google` (revoke old credentials first)

### POST /auth/refresh

Manually refresh access token.

**Request**:
```bash
curl -X POST http://localhost:8000/auth/refresh
```

**Response** (success):
```json
{
  "success": true,
  "message": "Access token refreshed successfully"
}
```

**Error Responses**:

Not authenticated:
```json
{
  "detail": "Not authenticated. No credentials to refresh."
}
```
Status: 401

No refresh token:
```json
{
  "detail": "No refresh token available. Please re-authenticate."
}
```
Status: 400

Refresh failed:
```json
{
  "detail": "Token refresh failed: invalid_grant"
}
```
Status: 401 - Re-authentication required

### POST /auth/revoke

Revoke credentials and delete tokens.

**Request**:
```bash
curl -X POST http://localhost:8000/auth/revoke
```

**Response**:
```json
{
  "success": true,
  "message": "Credentials revoked and deleted successfully"
}
```

**Process**:
1. Call Google's revoke endpoint: `https://oauth2.googleapis.com/revoke`
2. Delete local `data/token.json` file
3. Clear in-memory credentials

**Note**: Even if Google revoke fails (network issue), local tokens are deleted.

---

## Implementation Details

### OAuth Scopes

The application requests the following OAuth scope:

```
https://www.googleapis.com/auth/contacts.readonly
```

**Permissions**:
- ✅ Read contacts
- ✅ Read contact groups
- ❌ Create contacts (not requested)
- ❌ Update contacts (not requested)
- ❌ Delete contacts (not requested)

### OAuth Parameters

When initiating OAuth flow:

```python
params = {
    'client_id': settings.google_client_id,
    'redirect_uri': settings.google_redirect_uri,
    'scope': 'https://www.googleapis.com/auth/contacts.readonly',
    'access_type': 'offline',  # Request refresh token
    'response_type': 'code',
    'state': optional_redirect_uri,
    'prompt': 'consent'  # Force consent screen (ensures refresh token)
}
```

**Parameter Descriptions**:

- `access_type=offline`: Requests a refresh token for offline access
- `prompt=consent`: Forces the consent screen even if user previously granted access (ensures refresh token is issued)
- `state`: Used for CSRF protection and optional post-auth redirect

### Token Storage

Tokens are stored in JSON format at `data/token.json`:

**File Structure**:
```json
{
  "token": "access_token_here",
  "refresh_token": "refresh_token_here",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "client_id_here",
  "client_secret": "client_secret_here",
  "scopes": ["https://www.googleapis.com/auth/contacts.readonly"],
  "expiry": "2026-01-08T11:30:00.000000Z"
}
```

**File Permissions**:
```bash
chmod 600 data/token.json  # Read/write for owner only
```

### Credentials Loading

The application loads credentials from `token.json` on startup:

```python
def get_credentials() -> Optional[Credentials]:
    """Load credentials from token file."""
    if token_file.exists():
        return Credentials.from_authorized_user_file(
            str(token_file),
            scopes=[SCOPES]
        )
    return None
```

### Error Handling

Common OAuth errors and handling:

#### Invalid Client
```
Error: invalid_client
Cause: Client ID or secret is incorrect
Fix: Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
```

#### Invalid Grant
```
Error: invalid_grant
Cause: Refresh token is expired or revoked
Fix: Re-authenticate via /auth/google
```

#### Access Denied
```
Error: access_denied
Cause: User denied permissions
Fix: User must grant permissions for app to work
```

#### Redirect URI Mismatch
```
Error: redirect_uri_mismatch
Cause: Redirect URI doesn't match Google Console configuration
Fix: Update redirect URI in Google Console or .env
```

---

## Security Considerations

### Token Security

1. **File Permissions**
   ```bash
   chmod 600 data/token.json
   chown app:app data/token.json
   ```

2. **Environment Variables**
   - Never commit `.env` file
   - Use secure storage for production (e.g., secrets manager)

3. **Token Rotation**
   - Access tokens expire after 1 hour (automatic refresh)
   - Refresh tokens don't expire but can be revoked
   - Consider periodic re-authentication (e.g., every 6 months)

### OAuth Best Practices

1. **Use HTTPS in Production**
   - Tokens are transmitted during OAuth flow
   - Update redirect URI: `https://yourdomain.com/auth/callback`

2. **Validate State Parameter**
   - Prevents CSRF attacks
   - Application validates state on callback

3. **Minimal Scopes**
   - Only request `contacts.readonly` (not write access)
   - Reduces risk if token is compromised

4. **Secure Client Secret**
   - Never expose in client-side code
   - Store in environment variables
   - Rotate periodically

### Google OAuth Security Features

1. **Verified Apps**
   - For production, submit app for verification
   - Removes "This app isn't verified" warning

2. **OAuth Consent Screen**
   - Clearly describe data usage
   - Add privacy policy URL
   - List authorized domains

3. **Authorized Redirect URIs**
   - Whitelist specific redirect URIs in Google Console
   - Prevents token theft via redirect manipulation

---

## Troubleshooting

### Authentication Failed

**Symptom**: `authenticated: false` in status check

**Possible Causes**:
1. No token file exists
2. OAuth flow not completed
3. Tokens revoked by user

**Solutions**:
```bash
# Check token file
ls -la data/token.json

# Check auth status
curl http://localhost:8000/auth/status

# Re-authenticate
# Visit: http://localhost:8000/auth/google
```

### Token Refresh Failure

**Symptom**: `Token refresh failed: invalid_grant`

**Cause**: Refresh token is invalid or revoked

**Solution**:
```bash
# Revoke old credentials
curl -X POST http://localhost:8000/auth/revoke

# Re-authenticate
# Visit: http://localhost:8000/auth/google
```

### Redirect URI Mismatch

**Symptom**: Error page showing "redirect_uri_mismatch"

**Cause**: Redirect URI in request doesn't match Google Console configuration

**Solution**:
1. Check `.env` file:
   ```env
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
   ```

2. Check Google Cloud Console:
   - Go to: APIs & Services → Credentials
   - Edit OAuth 2.0 Client ID
   - Verify "Authorized redirect URIs" includes exact URI

3. Ensure protocol matches (http vs https)

### Insufficient Scopes

**Symptom**: API calls fail with "insufficient permissions"

**Cause**: Required scope not granted

**Solution**:
1. Check current scopes:
   ```bash
   curl http://localhost:8000/auth/status | jq .scopes
   ```

2. Expected scope:
   ```
   https://www.googleapis.com/auth/contacts.readonly
   ```

3. If missing, re-authenticate with correct scope

### Multiple Google Accounts

**Issue**: User has multiple Google accounts, confused about which one to use

**Solution**:
1. Use specific account hint:
   ```
   http://localhost:8000/auth/google?login_hint=user@example.com
   ```

2. Or use `prompt=select_account` to force account selection:
   ```python
   params['prompt'] = 'select_account'
   ```

### Token File Permissions Error

**Symptom**: `Permission denied: 'data/token.json'`

**Cause**: Application user doesn't have read/write permissions

**Solution**:
```bash
# Fix ownership
sudo chown $USER:$USER data/token.json

# Fix permissions
chmod 600 data/token.json
```

### Testing Mode Limitations

**Symptom**: "This app hasn't been verified" warning

**Cause**: OAuth app is in testing mode

**Solutions**:

1. **For Testing**:
   - Add your Gmail to "Test users" in Google Console
   - OAuth Consent Screen → Test users → Add Users

2. **For Production**:
   - Submit app for verification
   - OAuth Consent Screen → Publish App
   - Fill verification form

---

## Best Practices

### Development

1. **Use Separate OAuth Credentials**
   ```env
   # Development
   GOOGLE_CLIENT_ID=dev-client-id.apps.googleusercontent.com
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
   
   # Production
   GOOGLE_CLIENT_ID=prod-client-id.apps.googleusercontent.com
   GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback
   ```

2. **Test with Multiple Accounts**
   - Personal Gmail
   - Google Workspace account
   - Account with many contacts (>1000)

3. **Monitor OAuth Errors**
   ```bash
   # Check logs for auth errors
   grep "OAuth" /var/log/app.log
   ```

### Production

1. **Use HTTPS Only**
   ```nginx
   # Nginx redirect HTTP to HTTPS
   server {
       listen 80;
       return 301 https://$host$request_uri;
   }
   ```

2. **Implement Token Rotation**
   ```bash
   # Cron job to refresh tokens weekly
   0 0 * * 0 curl -X POST https://yourdomain.com/auth/refresh
   ```

3. **Monitor Token Health**
   ```python
   # Health check includes auth status
   @app.get("/health")
   async def health():
       auth_status = get_auth_status()
       return {
           "status": "healthy",
           "auth": auth_status["authenticated"]
       }
   ```

4. **Set Up Alerts**
   - Alert when auth fails
   - Alert when refresh token expires
   - Monitor failed API calls

---

## OAuth 2.0 Reference

### Official Documentation

- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [People API Auth](https://developers.google.com/people/v1/how-tos/authorizing)
- [OAuth 2.0 Scopes](https://developers.google.com/people/v1/how-tos/authorizing#OAuth20Authorizing)

### OAuth 2.0 Grant Types

This application uses the **Authorization Code Grant** flow, which is recommended for:
- Server-side applications
- Applications that can securely store client secrets
- Applications needing offline access (refresh tokens)

### Alternative Flows

Not used in this application:
- **Implicit Grant**: For client-side apps (less secure, no refresh token)
- **Client Credentials**: For service accounts (no user interaction)
- **Password Grant**: Deprecated, not recommended

---

## Conclusion

The authentication system provides secure, long-term access to Google Contacts using OAuth 2.0. Key features:

- ✅ Secure OAuth 2.0 flow
- ✅ Automatic token refresh
- ✅ Read-only access (minimal permissions)
- ✅ Manual token management API
- ✅ Comprehensive error handling
- ✅ Production-ready security

For additional help:
- [Setup Guide](setup.md) - Initial OAuth configuration
- [API Documentation](api.md) - Authentication API reference
- [Troubleshooting Guide](troubleshooting.md) - Common authentication issues
