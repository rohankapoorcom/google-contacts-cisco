# Reverse Proxy Setup Guide

This guide explains how to configure the application when deploying behind a reverse proxy (nginx, Traefik, Apache, etc.) with HTTPS termination.

## Problem

When using a reverse proxy that terminates SSL/TLS:

1. Client connects to proxy via HTTPS: `https://contacts.dev.rohankapoor.com`
2. Proxy terminates SSL and forwards to backend via HTTP: `http://backend:8000`
3. Backend sees HTTP requests, not HTTPS
4. OAuth library rejects token exchange with error: `(insecure_transport) OAuth 2 MUST utilize https`

## Solution

Enable proxy header trust by specifying trusted proxy IP addresses so the application correctly reconstructs the original HTTPS URL from proxy headers.

### Configuration

Set the trusted proxy IP addresses as a JSON array:

```bash
TRUSTED_PROXIES='["127.0.0.1", "172.17.0.0/16"]'
```

Add this to your `.env` file:

```env
# Reverse Proxy Settings
# List trusted proxy IPs that can send X-Forwarded-* headers (JSON array format)
TRUSTED_PROXIES=["127.0.0.1", "172.17.0.0/16"]
```

**For Docker/Docker Compose environment variables**, use JSON array format:

```yaml
environment:
  TRUSTED_PROXIES: '["127.0.0.1", "172.17.0.0/16"]'
```

Or for shell export:

```bash
export TRUSTED_PROXIES='["127.0.0.1", "172.17.0.0/16"]'
```

**Common proxy IP configurations:**
- **Local proxy on same host**: `TRUSTED_PROXIES='["127.0.0.1"]'`
- **Docker internal network**: `TRUSTED_PROXIES='["172.17.0.0/16"]'`
- **Multiple private networks**: `TRUSTED_PROXIES='["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]'`
- **Kubernetes pod network**: `TRUSTED_PROXIES='["10.244.0.0/16"]'` (depends on your CNI)
- **Specific proxy servers**: `TRUSTED_PROXIES='["192.168.1.50", "192.168.1.51"]'`

### How It Works

When `TRUSTED_PROXIES` is set:

1. Application validates requests come from trusted proxy IPs
2. Only accepts `X-Forwarded-Proto`, `X-Forwarded-Host`, and `X-Forwarded-For` headers from trusted sources
3. FastAPI's `request.url` reflects the original HTTPS scheme
4. OAuth callback works correctly with HTTPS URLs

### Security Benefits

This approach is more secure than blindly trusting all proxies:
- **IP validation**: Only accepts forwarded headers from known proxy IPs
- **Prevents spoofing**: Untrusted clients cannot forge X-Forwarded-* headers
- **Defense in depth**: Even if application is accidentally exposed, headers are validated

### Reverse Proxy Configuration

Ensure your reverse proxy forwards the necessary headers:

#### Nginx

```nginx
location / {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
}
```

#### Traefik

Traefik automatically adds these headers when configured correctly. No additional configuration needed.

#### Apache

```apache
ProxyPass / http://backend:8000/
ProxyPassReverse / http://backend:8000/
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-Host %{HTTP_HOST}e
```

### Security Considerations

**IMPORTANT**: Only add IP addresses of trusted reverse proxies to `TRUSTED_PROXIES`.

The application will only accept `X-Forwarded-*` headers from these IP addresses:
- ✅ **Safe**: Add only your reverse proxy's internal IP address
- ✅ **Safe**: Use CIDR notation for proxy network ranges
- ❌ **Unsafe**: Adding `0.0.0.0/0` or public internet IPs
- ❌ **Unsafe**: Adding client IP ranges (only proxy IPs should be trusted)

**Best Practices:**
1. Use the most specific IP/CIDR range possible
2. Regularly review and update the trusted proxy list
3. Monitor logs for untrusted proxy warnings
4. Never trust the entire internet (`0.0.0.0/0`)

### OAuth Redirect URI

Configure your Google OAuth redirect URI with the HTTPS URL:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services → Credentials
3. Edit your OAuth 2.0 Client ID
4. Add authorized redirect URI: `https://contacts.dev.rohankapoor.com/auth/callback`

### Determining Your Proxy IP Address

To find your reverse proxy's IP address:

```bash
# If running in Docker Compose, check the gateway IP
docker network inspect google-contacts-cisco_default | grep Gateway

# If running with systemd, check who connects to the backend
sudo netstat -tnlp | grep :8000

# From nginx access logs
tail -f /var/log/nginx/access.log

# The connecting IP will be your proxy's IP address
```

### Verification

After configuration, test the OAuth flow:

1. Visit: `https://contacts.dev.rohankapoor.com/auth/google`
2. Complete Google authentication
3. Callback should succeed without the `insecure_transport` error

Check application logs for confirmation:

```
Proxy headers middleware enabled - trusting X-Forwarded-* headers from: 127.0.0.1, 172.17.0.0/16
OAuth callback processed successfully
```

If you see warnings about untrusted proxies, adjust your `TRUSTED_PROXIES` setting:

```
WARNING: Received X-Forwarded headers from untrusted source: 172.18.0.1
```

### Alternative Approaches (Not Recommended)

#### Option 1: Trust All Proxies (Less Secure)

If you cannot determine proxy IPs, you can trust all sources:

```env
TRUSTED_PROXIES=0.0.0.0/0
```

**⚠️ WARNING**: This trusts X-Forwarded headers from anyone. Only use for testing or if application is not publicly accessible.

#### Option 2: Bypass Transport Security (Least Secure)

Force the OAuth library to allow HTTP:

```env
OAUTHLIB_INSECURE_TRANSPORT=1
```

**⚠️ WARNING**: This bypasses OAuth transport security checks entirely. Only use as a last resort for local development.

### Troubleshooting

#### Still Getting insecure_transport Error

1. Verify `TRUSTED_PROXIES` contains your proxy's IP address
2. Check application logs show: "Proxy headers middleware enabled - trusting X-Forwarded-* headers from: [your IPs]"
3. Verify proxy is sending `X-Forwarded-Proto: https` header
4. Check for warnings about untrusted proxy sources in logs
5. Restart the application after changing environment variables

#### Other OAuth Errors

1. Verify redirect URI matches exactly in Google Console
2. Check Google OAuth credentials are correct
3. Ensure proxy is forwarding all necessary headers
4. Review application logs for detailed error messages

#### Testing Proxy Headers

You can test if headers are being forwarded correctly:

```bash
# From the backend, check what headers the app receives
curl -H "X-Forwarded-Proto: https" \
     -H "X-Forwarded-Host: contacts.dev.rohankapoor.com" \
     http://localhost:8000/health
```

## Summary

For reverse proxy deployments:

1. ✅ Determine your reverse proxy's IP address(es)
2. ✅ Set `TRUSTED_PROXIES` with those specific IPs/CIDR ranges
3. ✅ Configure reverse proxy to forward `X-Forwarded-*` headers  
4. ✅ Use HTTPS URL in Google OAuth redirect URI configuration
5. ✅ Verify in logs that proxy middleware is enabled
6. ✅ Test OAuth flow works without insecure_transport error
