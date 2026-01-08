# Troubleshooting Guide

## Overview

This guide provides solutions to common issues you may encounter while using the Google Contacts to Cisco IP Phone application. Issues are organized by category for easy navigation.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Authentication Issues](#authentication-issues)
3. [Synchronization Issues](#synchronization-issues)
4. [API Issues](#api-issues)
5. [Cisco Phone Issues](#cisco-phone-issues)
6. [Performance Issues](#performance-issues)
7. [Database Issues](#database-issues)
8. [Networking Issues](#networking-issues)
9. [Configuration Issues](#configuration-issues)
10. [Getting Help](#getting-help)

---

## Installation Issues

### Cannot Install Dependencies

**Error**: `pip install` fails with dependency conflicts

**Causes**:
- Python version incompatibility
- Conflicting packages in system Python
- Missing system dependencies

**Solutions**:

```bash
# Solution 1: Use uv (recommended)
pip install uv
uv venv
source .venv/bin/activate
uv pip install -e .

# Solution 2: Update pip and retry
pip install --upgrade pip setuptools wheel
pip install -e .

# Solution 3: Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3-dev gcc libssl-dev

# Solution 4: Use fresh virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Alembic Migration Fails

**Error**: `alembic upgrade head` fails

**Cause**: Database file exists with wrong schema

**Solution**:

```bash
# Backup existing database
cp data/contacts.db data/contacts.db.backup

# Remove database
rm data/contacts.db

# Re-run migrations
uv run alembic upgrade head

# If you need the old data, export/import:
# Export from backup: sqlite3 data/contacts.db.backup ".dump" > backup.sql
# Import to new db: sqlite3 data/contacts.db < backup.sql
```

### Port Already in Use

**Error**: `Address already in use: ('0.0.0.0', 8000)`

**Solution**:

```bash
# Find process using port 8000
lsof -i :8000
# Or
sudo netstat -tulpn | grep 8000

# Kill process
kill -9 <PID>

# Or use different port
# Edit .env:
PORT=8001

# Restart application
```

---

## Authentication Issues

### OAuth Credentials Not Configured

**Error**: `Google OAuth credentials not configured`

**Cause**: Missing or incorrect credentials in `.env`

**Solution**:

```bash
# 1. Check .env file exists
ls -la .env

# 2. Verify credentials are set
grep "GOOGLE_CLIENT" .env

# 3. Ensure no extra spaces or quotes
# Correct format:
GOOGLE_CLIENT_ID=1234567890-abc123.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456

# 4. Restart application
sudo systemctl restart google-contacts-cisco
```

### Redirect URI Mismatch

**Error**: `redirect_uri_mismatch` in OAuth flow

**Cause**: Redirect URI doesn't match Google Console configuration

**Solution**:

1. **Check `.env` file**:
   ```env
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
   ```

2. **Check Google Cloud Console**:
   - Go to APIs & Services → Credentials
   - Edit OAuth 2.0 Client ID
   - Verify "Authorized redirect URIs" includes **exact** URI (including protocol)

3. **Common mistakes**:
   - ❌ `http://localhost:8000/callback` (wrong path)
   - ❌ `https://localhost:8000/auth/callback` (http vs https)
   - ❌ `http://localhost/auth/callback` (missing port)
   - ✅ `http://localhost:8000/auth/callback` (correct)

4. **For production**:
   ```env
   GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback
   ```

### Token Refresh Failed: invalid_grant

**Error**: `Token refresh failed: invalid_grant`

**Causes**:
- Refresh token expired or revoked
- User revoked access in Google account settings
- OAuth credentials changed

**Solution**:

```bash
# 1. Revoke old credentials
curl -X POST http://localhost:8000/auth/revoke

# 2. Delete token file
rm data/token.json

# 3. Re-authenticate
# Visit: http://localhost:8000/auth/google

# 4. Complete OAuth flow
# Follow prompts to grant permissions

# 5. Verify authentication
curl http://localhost:8000/auth/status
```

### This App Hasn't Been Verified

**Warning**: "This app hasn't been verified by Google"

**Cause**: OAuth app is in testing mode

**Solutions**:

**For Development/Testing**:
1. Click "Advanced"
2. Click "Go to [App Name] (unsafe)"
3. Continue with OAuth flow

**For Production**:
1. Add users to test users list (OAuth Consent Screen → Test users)
2. Or submit app for verification:
   - OAuth Consent Screen → "Publish App"
   - Fill out verification form
   - Wait for Google approval (can take weeks)

### Authentication Status Shows Not Authenticated

**Symptom**: `{"authenticated": false}` even after OAuth

**Causes**:
- Token file not created
- Token file in wrong location
- File permission issues

**Solution**:

```bash
# 1. Check token file exists
ls -la data/token.json

# 2. Check file permissions
# Should be readable by application user
chmod 600 data/token.json
chown contacts:contacts data/token.json  # If running as 'contacts' user

# 3. Check token file content
cat data/token.json
# Should contain JSON with token, refresh_token, etc.

# 4. Check TOKEN_FILE setting in .env
grep TOKEN_FILE .env
# Should match actual location

# 5. Re-authenticate if needed
curl -X POST http://localhost:8000/auth/revoke
# Visit: http://localhost:8000/auth/google
```

---

## Synchronization Issues

### Sync Fails with 401 Unauthorized

**Error**: Sync returns 401 error

**Cause**: Invalid or expired credentials

**Solution**:

```bash
# 1. Check auth status
curl http://localhost:8000/auth/status

# 2. Try refreshing token
curl -X POST http://localhost:8000/auth/refresh

# 3. If refresh fails, re-authenticate
curl -X POST http://localhost:8000/auth/revoke
# Visit: http://localhost:8000/auth/google
```

### Sync Hangs or Times Out

**Symptom**: Sync request never completes

**Causes**:
- Large contact list (>10,000 contacts)
- Network connectivity issues
- Google API rate limiting

**Solutions**:

```bash
# 1. Check sync status
curl http://localhost:8000/api/sync/status

# 2. Check if sync is actually running
# Look for high CPU usage
top

# 3. Check application logs
sudo journalctl -u google-contacts-cisco -f

# 4. If stuck, restart service
sudo systemctl restart google-contacts-cisco

# 5. Try incremental sync instead of full
curl -X POST http://localhost:8000/api/sync/incremental

# 6. For very large contact lists, increase timeout
# Edit systemd service: TimeoutStartSec=600
```

### Sync Completes But No Contacts

**Symptom**: Sync successful but contact count is 0

**Causes**:
- No contacts in Google account
- Contacts are in "Other contacts" (not synced)
- API scope issue

**Solutions**:

```bash
# 1. Check sync statistics
curl http://localhost:8000/api/sync/statistics

# 2. Check Google account has contacts
# Visit: https://contacts.google.com

# 3. Check OAuth scopes
curl http://localhost:8000/auth/status | jq .scopes
# Should include: https://www.googleapis.com/auth/contacts.readonly

# 4. Test Google API connection
curl http://localhost:8000/api/test-connection

# 5. Try full sync
curl -X POST http://localhost:8000/api/sync/full
```

### Sync Token Expired (410 Error)

**Error**: `Sync token expired or invalid (HTTP 410)`

**Cause**: Sync token expired (typically after 7 days of no sync)

**Solution**:

This is handled automatically! The application falls back to full sync when the sync token expires.

```bash
# Manually trigger full sync
curl -X POST http://localhost:8000/api/sync/full

# Or use auto sync (automatically chooses full or incremental)
curl -X POST http://localhost:8000/api/sync
```

### Rate Limit Exceeded

**Error**: `Rate limit exceeded` (HTTP 429)

**Cause**: Too many API requests to Google

**Solutions**:

1. **Wait and Retry**:
   ```bash
   # Wait 60 seconds
   sleep 60
   curl -X POST http://localhost:8000/api/sync
   ```

2. **Use Incremental Sync**:
   ```bash
   # Less API calls than full sync
   curl -X POST http://localhost:8000/api/sync/incremental
   ```

3. **Enable Sync Scheduler** (instead of manual syncs):
   ```env
   # In .env
   SYNC_SCHEDULER_ENABLED=true
   SYNC_INTERVAL_MINUTES=30
   ```

4. **Check Google API Quota**:
   - Go to Google Cloud Console → APIs & Services → Dashboard
   - View quota usage
   - Request quota increase if needed

---

## API Issues

### API Returns 500 Internal Server Error

**Error**: Generic 500 error on API calls

**Causes**:
- Application crash
- Database corruption
- Unhandled exception

**Solutions**:

```bash
# 1. Check application logs
sudo journalctl -u google-contacts-cisco -n 100

# 2. Check error details
curl -v http://localhost:8000/api/contacts 2>&1 | grep -A 10 "< HTTP"

# 3. Restart application
sudo systemctl restart google-contacts-cisco

# 4. Check database integrity
sqlite3 data/contacts.db "PRAGMA integrity_check;"

# 5. If database is corrupted, restore from backup
cp /var/backups/google-contacts-cisco/backup_latest.tar.gz .
tar -xzf backup_latest.tar.gz
cp contacts_*.db data/contacts.db
```

### Search Returns No Results

**Symptom**: Search API returns empty results for existing contacts

**Causes**:
- Search query too short
- Database not populated
- Search index issue

**Solutions**:

```bash
# 1. Check contact count
curl http://localhost:8000/api/contacts/stats

# 2. Try listing contacts
curl http://localhost:8000/api/contacts?limit=5

# 3. Check search query length (minimum 2 characters)
curl "http://localhost:8000/api/search?q=john"

# 4. Rebuild search index (if using FTS)
# This is automatic, but can be forced by re-syncing
curl -X POST http://localhost:8000/api/sync/full
```

### CORS Errors in Browser

**Error**: `Access-Control-Allow-Origin` errors in browser console

**Cause**: Frontend running on different port than API

**Solutions**:

**For Development**:
1. Frontend and API are on different ports (expected)
2. Check CORS is enabled in `main.py`:
   ```python
   # Should include frontend origin
   allow_origins=["http://localhost:5173"]
   ```

**For Production**:
1. Use reverse proxy (Nginx) to serve both on same domain
2. Or configure CORS to allow production frontend domain:
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

---

## Cisco Phone Issues

### Phone Shows "Service Not Available"

**Causes**:
- Server not running
- Network connectivity
- Wrong URL configured
- Firewall blocking

**Solutions**:

```bash
# 1. Check server is running
curl http://YOUR_SERVER:8000/health

# 2. Test from phone network
# From a computer on same network as phone:
curl http://YOUR_SERVER:8000/directory

# 3. Check firewall
sudo ufw status
# Should allow port 8000 from phone subnet

# 4. Verify URL in phone config
# Should be exact: http://YOUR_SERVER:8000/directory

# 5. Check DNS resolution (if using hostname)
nslookup YOUR_SERVER

# 6. Test with IP address instead
http://192.168.1.100:8000/directory
```

### Directory Loads But Shows "No Contacts"

**Causes**:
- No contacts synced
- All contacts deleted
- Grouping issue

**Solutions**:

```bash
# 1. Check contact count
curl http://YOUR_SERVER:8000/api/contacts/stats

# 2. Check sync status
curl http://YOUR_SERVER:8000/api/sync/status

# 3. Sync contacts
curl -X POST http://YOUR_SERVER:8000/api/sync

# 4. Test directory XML
curl http://YOUR_SERVER:8000/directory/groups/2ABC
# Should show contacts starting with 2, A, B, or C
```

### XML Parsing Error on Phone

**Symptoms**: Phone shows "XML Error" or blank screen

**Causes**:
- Invalid XML
- XML too large
- Character encoding issues

**Solutions**:

```bash
# 1. Validate XML
curl http://YOUR_SERVER:8000/directory | xmllint --format - > /dev/null
# Should show no errors

# 2. Check XML size
curl http://YOUR_SERVER:8000/directory | wc -c
# Should be < 4096 bytes for most phones

# 3. Check for special characters
curl http://YOUR_SERVER:8000/directory | grep -P "[^\x00-\x7F]"

# 4. View XML in browser
# Visit: http://YOUR_SERVER:8000/directory
# Check for proper formatting
```

### Contact Names Show Incorrectly

**Symptoms**: Special characters show as ??? or boxes

**Causes**:
- Encoding issue
- Phone firmware doesn't support UTF-8
- Character set incompatibility

**Solutions**:

1. **Update Phone Firmware**:
   - Latest firmware has better Unicode support

2. **Check XML Encoding**:
   ```bash
   curl http://YOUR_SERVER:8000/directory | head -1
   # Should show: <?xml version="1.0" encoding="UTF-8"?>
   ```

3. **Test with ASCII-only contact**:
   - Create a contact with only ASCII characters
   - If it works, issue is with Unicode support

### Phone Can't Dial Numbers

**Symptoms**: Selecting number doesn't initiate call

**Causes**:
- Number format incompatible
- Phone system requires specific format
- Dial plan restrictions

**Solutions**:

1. **Check Number Format**:
   ```bash
   # Numbers should be in E.164 format: +1234567890
   curl http://YOUR_SERVER:8000/api/contacts?limit=1 | jq '.contacts[0].phone_numbers'
   ```

2. **Test Manual Dial**:
   - Manually dial the number from phone keypad
   - If manual dial works, issue is with XML dial command

3. **Check CUCM Dial Plan** (if applicable):
   - Verify external dialing works
   - May need prefix (e.g., 9 for outside line)

4. **Future Enhancement**:
   - Add dial plan transformation
   - Configure number formatting per deployment

---

## Performance Issues

### Slow API Responses

**Symptoms**: API requests take > 1 second

**Causes**:
- Large database
- Missing indexes
- Server under load
- Network latency

**Solutions**:

```bash
# 1. Check database size
ls -lh data/contacts.db

# 2. Optimize database
sqlite3 data/contacts.db "VACUUM; ANALYZE;"

# 3. Check server resources
top
free -h
df -h

# 4. Enable caching (if using nginx)
# Add proxy_cache directives

# 5. Increase workers (if using Gunicorn)
# Edit systemd service:
--workers 9  # (2 x CPU cores) + 1

# 6. Monitor slow queries
# Check application logs for slow operations
```

### High Memory Usage

**Symptoms**: Application using > 500MB RAM

**Causes**:
- Large contact list
- Memory leak
- Many workers

**Solutions**:

```bash
# 1. Check memory usage
ps aux | grep uvicorn

# 2. Reduce workers
# Edit systemd service: --workers 4

# 3. Restart service regularly (if memory leak)
# Add to cron:
0 3 * * * systemctl restart google-contacts-cisco

# 4. Monitor for memory leaks
# Watch memory over time:
watch -n 5 'ps aux | grep uvicorn | head -1'
```

### Database Growing Too Large

**Symptoms**: `contacts.db` > 1GB

**Causes**:
- Many contacts (>50,000)
- Sync history accumulation
- No cleanup

**Solutions**:

```bash
# 1. Check database size
ls -lh data/contacts.db

# 2. Clear old sync history
curl -X DELETE "http://localhost:8000/api/sync/history?keep_latest=true"

# 3. Vacuum database
sqlite3 data/contacts.db "VACUUM;"

# 4. For extremely large databases, consider PostgreSQL
# (Future enhancement)
```

---

## Database Issues

### Database Locked

**Error**: `database is locked`

**Causes**:
- Multiple processes accessing database
- Long-running transaction
- SQLite limitation

**Solutions**:

```bash
# 1. Check for multiple processes
ps aux | grep uvicorn
# Should only see one master process

# 2. Restart application
sudo systemctl restart google-contacts-cisco

# 3. If persistent, check for file locks
lsof data/contacts.db

# 4. For production with high concurrency, consider PostgreSQL
```

### Database Corruption

**Error**: `database disk image is malformed`

**Cause**: Disk error, power loss, or improper shutdown

**Solutions**:

```bash
# 1. Stop application
sudo systemctl stop google-contacts-cisco

# 2. Backup corrupted database
cp data/contacts.db data/contacts.db.corrupted

# 3. Try to repair
sqlite3 data/contacts.db ".recover" | sqlite3 data/contacts_recovered.db

# 4. Or restore from backup
cp /var/backups/google-contacts-cisco/backup_latest.tar.gz .
tar -xzf backup_latest.tar.gz
cp contacts_*.db data/contacts.db

# 5. Start application
sudo systemctl start google-contacts-cisco

# 6. Re-sync if needed
curl -X POST http://localhost:8000/api/sync/full
```

---

## Networking Issues

### Cannot Connect to Google API

**Error**: Connection timeout or network error

**Causes**:
- No internet connection
- Firewall blocking outbound HTTPS
- Proxy configuration needed

**Solutions**:

```bash
# 1. Test internet connectivity
ping 8.8.8.8
curl https://www.google.com

# 2. Test Google API specifically
curl https://people.googleapis.com/

# 3. Check DNS resolution
nslookup people.googleapis.com

# 4. If behind proxy, configure environment variables
export HTTPS_PROXY=http://proxy.example.com:8080
export HTTP_PROXY=http://proxy.example.com:8080

# 5. Add to .env or systemd service environment
```

### SSL Certificate Verification Failed

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Cause**: System CA certificates not installed or outdated

**Solutions**:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ca-certificates
sudo update-ca-certificates

# CentOS/RHEL
sudo yum install ca-certificates
sudo update-ca-trust

# If using corporate SSL inspection, add corporate CA
sudo cp corporate-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

---

## Configuration Issues

### Environment Variables Not Loading

**Symptom**: Application uses defaults instead of `.env` values

**Causes**:
- `.env` file not in correct location
- Syntax errors in `.env`
- systemd service not loading `.env`

**Solutions**:

```bash
# 1. Check .env location
ls -la .env
# Should be in application root directory

# 2. Check .env syntax
cat .env
# No spaces around =
# No quotes unless needed

# 3. For systemd, verify EnvironmentFile
systemctl cat google-contacts-cisco | grep EnvironmentFile
# Should point to correct .env file

# 4. Test configuration
uv run python -c "from google_contacts_cisco.config import settings; print(settings.dict())"
```

### Configuration Validation Fails

**Error**: Configuration warnings on startup

**Causes**:
- Missing required settings
- Invalid values

**Solutions**:

```bash
# 1. Run configuration validation
uv run python -m google_contacts_cisco.config_utils

# 2. Check for specific errors
# Fix any reported issues

# 3. Required settings for production:
# - GOOGLE_CLIENT_ID
# - GOOGLE_CLIENT_SECRET
# - GOOGLE_REDIRECT_URI
# - DATABASE_URL
```

---

## Getting Help

### Diagnostic Information

When reporting issues, provide:

```bash
# 1. Application version
curl http://localhost:8000/health | jq .version

# 2. Configuration status
curl http://localhost:8000/health | jq .config_valid

# 3. Authentication status
curl http://localhost:8000/auth/status

# 4. Recent logs
sudo journalctl -u google-contacts-cisco -n 100

# 5. System information
uname -a
python --version
```

### Common Log Patterns

**Authentication Issues**:
```bash
sudo journalctl -u google-contacts-cisco | grep -i "oauth\|auth\|token"
```

**Sync Issues**:
```bash
sudo journalctl -u google-contacts-cisco | grep -i "sync\|google api"
```

**Database Issues**:
```bash
sudo journalctl -u google-contacts-cisco | grep -i "database\|sqlite"
```

### Enable Debug Logging

Temporarily enable debug logging:

```bash
# Edit .env
DEBUG=true
LOG_LEVEL=DEBUG

# Restart application
sudo systemctl restart google-contacts-cisco

# View debug logs
sudo journalctl -u google-contacts-cisco -f

# Don't forget to disable in production!
DEBUG=false
LOG_LEVEL=INFO
```

### Resources

- **API Documentation**: [api.md](api.md)
- **Setup Guide**: [setup.md](setup.md)
- **Authentication Guide**: [authentication.md](authentication.md)
- **Deployment Guide**: [deployment.md](deployment.md)
- **Cisco Phone Setup**: [cisco-phone-setup.md](cisco-phone-setup.md)

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Conclusion

This troubleshooting guide covers the most common issues. If your issue isn't covered:

1. Check application logs for detailed error messages
2. Search existing issues in the repository
3. Review relevant documentation
4. Enable debug logging for more information

Remember to disable debug mode and restart the application after troubleshooting is complete.
