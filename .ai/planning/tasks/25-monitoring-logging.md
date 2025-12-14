# Task 8.3: Monitoring and Logging

## Overview

Implement comprehensive monitoring, logging, and observability infrastructure to track application health, performance metrics, errors, and usage patterns in production with Prometheus metrics, structured logging, and alerting.

## Priority

**P2 (Medium)** - Important for production operations and maintenance

## Dependencies

- Task 8.2: Deployment Preparation
- All implementation tasks

## Objectives

1. Configure structured JSON logging with context
2. Implement Prometheus metrics collection
3. Create comprehensive health check endpoints
4. Add request tracing with unique IDs
5. Set up error tracking and notifications
6. Create Grafana monitoring dashboard
7. Configure log rotation and retention
8. Set up alerting rules
9. Add performance profiling
10. Document monitoring procedures

## Technical Context

### Monitoring Architecture
```
Application → Logs (JSON) → Log Aggregator (optional)
           → Metrics (/metrics) → Prometheus → Grafana
           → Health Checks → Monitoring System
```

### Metrics Types
- **Counters**: Request counts, sync counts, errors
- **Histograms**: Request duration, sync duration
- **Gauges**: Contact count, database size, memory usage

### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages  
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error events that might still allow application to continue
- **CRITICAL**: Severe errors causing application failure

## Acceptance Criteria

- [ ] Structured JSON logging configured
- [ ] All requests logged with timing
- [ ] Prometheus metrics exposed at `/metrics`
- [ ] Health check returns component status
- [ ] Request IDs track requests end-to-end
- [ ] Errors logged with full context
- [ ] Log rotation prevents disk filling
- [ ] Grafana dashboard created
- [ ] Alert rules configured
- [ ] Documentation complete

## Implementation Steps

### 1. Install Monitoring Dependencies

Update `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "python-json-logger>=2.0.7",
    "prometheus-client>=0.19.0",
]
```

### 2. Create Enhanced Logger

Create `google_contacts_cisco/utils/logger.py`:

```python
"""Enhanced structured logging."""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ):
        """Add custom fields to log record.
        
        Args:
            log_record: Log record dictionary
            record: Logging record
            message_dict: Message dictionary
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add level and logger name
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add source location
        log_record['file'] = record.filename
        log_record['line'] = record.lineno
        log_record['function'] = record.funcName
        
        # Add custom context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms
        
        if hasattr(record, 'status_code'):
            log_record['status_code'] = record.status_code


def setup_logging(
    level: str = "INFO",
    log_dir: Path = None,
    json_format: bool = True
) -> logging.Logger:
    """Set up application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        json_format: Use JSON format for structured logging
        
    Returns:
        Configured root logger
    """
    # Get root logger
    logger = logging.getLogger("google_contacts_cisco")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handlers (if log_dir provided)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # All logs
        all_handler = logging.FileHandler(log_dir / "app.log")
        all_handler.setLevel(logging.INFO)
        all_handler.setFormatter(formatter)
        logger.addHandler(all_handler)
        
        # Error logs only
        error_handler = logging.FileHandler(log_dir / "errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # Access logs (INFO only)
        access_handler = logging.FileHandler(log_dir / "access.log")
        access_handler.setLevel(logging.INFO)
        access_handler.addFilter(lambda record: record.levelno == logging.INFO)
        access_handler.setFormatter(formatter)
        logger.addHandler(access_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"google_contacts_cisco.{name}")
```

### 3. Create Request Logging Middleware

Create `google_contacts_cisco/middleware/logging.py`:

```python
"""Logging middleware for HTTP requests."""
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from ..utils.logger import get_logger
from ..monitoring.metrics import MetricsCollector

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with timing and context."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Start timer
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "Request received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )
            
            # Record metrics
            MetricsCollector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration_ms / 1000
            )
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            
            # Record error metrics
            MetricsCollector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
                duration=duration_ms / 1000
            )
            
            # Re-raise to let FastAPI handle
            raise
```

### 4. Implement Prometheus Metrics

Create `google_contacts_cisco/monitoring/metrics.py`:

```python
"""Prometheus metrics collection."""
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import Response
from pathlib import Path

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Business metrics
contacts_total = Gauge(
    'contacts_total',
    'Total number of contacts in database'
)

sync_duration_seconds = Histogram(
    'sync_duration_seconds',
    'Duration of contact sync operations',
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

sync_operations_total = Counter(
    'sync_operations_total',
    'Total number of sync operations',
    ['type', 'status']
)

contacts_synced_total = Counter(
    'contacts_synced_total',
    'Total contacts synced',
    ['operation']  # added, updated, deleted
)

# Search metrics
search_requests_total = Counter(
    'search_requests_total',
    'Total search requests',
    ['type']  # name, phone, general
)

search_duration_seconds = Histogram(
    'search_duration_seconds',
    'Search query duration in seconds',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

search_results_count = Histogram(
    'search_results_count',
    'Number of search results returned',
    buckets=[0, 1, 5, 10, 25, 50, 100]
)

# Database metrics
database_size_bytes = Gauge(
    'database_size_bytes',
    'Size of SQLite database file in bytes'
)

database_queries_total = Counter(
    'database_queries_total',
    'Total database queries',
    ['operation']  # select, insert, update, delete
)

# OAuth metrics
oauth_token_refreshes_total = Counter(
    'oauth_token_refreshes_total',
    'Total OAuth token refreshes',
    ['status']  # success, failure
)

# Application info
app_info = Info(
    'application',
    'Application information'
)


class MetricsCollector:
    """Collect and update application metrics."""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics.
        
        Args:
            method: HTTP method
            endpoint: Endpoint path
            status_code: Response status code
            duration: Request duration in seconds
        """
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @staticmethod
    def update_contact_count(count: int):
        """Update total contact count.
        
        Args:
            count: Number of contacts
        """
        contacts_total.set(count)
    
    @staticmethod
    def record_sync(
        sync_type: str,
        success: bool,
        duration: float,
        added: int = 0,
        updated: int = 0,
        deleted: int = 0
    ):
        """Record sync operation metrics.
        
        Args:
            sync_type: Type of sync (full, incremental)
            success: Whether sync succeeded
            duration: Sync duration in seconds
            added: Number of contacts added
            updated: Number of contacts updated
            deleted: Number of contacts deleted
        """
        status = "success" if success else "failure"
        
        sync_operations_total.labels(
            type=sync_type,
            status=status
        ).inc()
        
        sync_duration_seconds.observe(duration)
        
        if success:
            if added > 0:
                contacts_synced_total.labels(operation="added").inc(added)
            if updated > 0:
                contacts_synced_total.labels(operation="updated").inc(updated)
            if deleted > 0:
                contacts_synced_total.labels(operation="deleted").inc(deleted)
    
    @staticmethod
    def record_search(
        search_type: str,
        duration: float,
        result_count: int
    ):
        """Record search metrics.
        
        Args:
            search_type: Type of search (name, phone, general)
            duration: Search duration in seconds
            result_count: Number of results returned
        """
        search_requests_total.labels(type=search_type).inc()
        search_duration_seconds.observe(duration)
        search_results_count.observe(result_count)
    
    @staticmethod
    def update_database_size(size_bytes: int):
        """Update database size metric.
        
        Args:
            size_bytes: Database size in bytes
        """
        database_size_bytes.set(size_bytes)
    
    @staticmethod
    def record_database_query(operation: str):
        """Record database query.
        
        Args:
            operation: Query type (select, insert, update, delete)
        """
        database_queries_total.labels(operation=operation).inc()
    
    @staticmethod
    def record_oauth_refresh(success: bool):
        """Record OAuth token refresh.
        
        Args:
            success: Whether refresh succeeded
        """
        status = "success" if success else "failure"
        oauth_token_refreshes_total.labels(status=status).inc()
    
    @staticmethod
    def set_app_info(version: str, python_version: str):
        """Set application information.
        
        Args:
            version: Application version
            python_version: Python version
        """
        app_info.info({
            'version': version,
            'python_version': python_version
        })


def get_prometheus_metrics() -> Response:
    """Get Prometheus metrics.
    
    Returns:
        Response with metrics in Prometheus exposition format
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

### 5. Add Metrics Endpoint and Middleware

Update `google_contacts_cisco/main.py`:

```python
"""Main application with monitoring."""
import sys
from pathlib import Path

from google_contacts_cisco._version import __version__
from google_contacts_cisco.middleware.logging import RequestLoggingMiddleware
from google_contacts_cisco.monitoring.metrics import (
    get_prometheus_metrics,
    MetricsCollector
)
from google_contacts_cisco.utils.logger import setup_logging

# Set up logging
setup_logging(
    level=settings.log_level,
    log_dir=Path("logs"),
    json_format=settings.environment == "production"
)

# Initialize app
app = FastAPI(
    title="Google Contacts Cisco Directory",
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Set application info metrics
MetricsCollector.set_app_info(
    version=__version__,
    python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.
    
    Exposes application metrics in Prometheus exposition format.
    This endpoint should be scraped by Prometheus at regular intervals.
    """
    return get_prometheus_metrics()


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    from .models import get_db
    from .models.contact import Contact
    
    logger.info(f"Starting application version {__version__}")
    
    # Update initial contact count metric
    db = next(get_db())
    try:
        count = db.query(Contact).filter(Contact.deleted == False).count()
        MetricsCollector.update_contact_count(count)
        logger.info(f"Initial contact count: {count}")
    finally:
        db.close()
    
    # Update database size metric
    db_path = Path("data/contacts.db")
    if db_path.exists():
        size = db_path.stat().st_size
        MetricsCollector.update_database_size(size)
        logger.info(f"Database size: {size / 1024 / 1024:.2f}MB")
```

### 6. Create Periodic Metrics Update Task

Create `google_contacts_cisco/monitoring/background_tasks.py`:

```python
"""Background tasks for metrics collection."""
import asyncio
from pathlib import Path

from ..models import get_db
from ..models.contact import Contact
from ..utils.logger import get_logger
from .metrics import MetricsCollector

logger = get_logger(__name__)


async def update_metrics_periodically(interval: int = 60):
    """Update metrics periodically.
    
    Args:
        interval: Update interval in seconds
    """
    while True:
        try:
            await update_metrics()
        except Exception as e:
            logger.error(f"Error updating metrics: {e}", exc_info=True)
        
        await asyncio.sleep(interval)


async def update_metrics():
    """Update all metrics."""
    db = next(get_db())
    
    try:
        # Update contact count
        count = db.query(Contact).filter(Contact.deleted == False).count()
        MetricsCollector.update_contact_count(count)
        
        # Update database size
        db_path = Path("data/contacts.db")
        if db_path.exists():
            size = db_path.stat().st_size
            MetricsCollector.update_database_size(size)
    
    finally:
        db.close()


# Start background task
@app.on_event("startup")
async def start_metrics_updater():
    """Start periodic metrics updater."""
    asyncio.create_task(update_metrics_periodically())
```

### 7. Create Alert Rules

Create `monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: google_contacts_cisco_alerts
    interval: 30s
    rules:
      # Application Health
      - alert: ApplicationDown
        expr: up{job="contacts-app"} == 0
        for: 2m
        labels:
          severity: critical
          component: application
        annotations:
          summary: "Application is down"
          description: "The Google Contacts Cisco application has been unreachable for more than 2 minutes"
          runbook_url: "https://docs.example.com/runbooks/app-down"
      
      # Error Rate
      - alert: HighErrorRate
        expr: |
          (
            rate(http_requests_total{status=~"5.."}[5m]) 
            / 
            rate(http_requests_total[5m])
          ) > 0.05
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "High error rate detected"
          description: "More than 5% of requests are failing ({{ $value | humanizePercentage }})"
          runbook_url: "https://docs.example.com/runbooks/high-error-rate"
      
      # Response Time
      - alert: HighResponseTime
        expr: |
          histogram_quantile(
            0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 10m
        labels:
          severity: warning
          component: performance
        annotations:
          summary: "High API response time"
          description: "95th percentile response time is {{ $value | humanizeDuration }}"
          runbook_url: "https://docs.example.com/runbooks/slow-responses"
      
      # Directory Performance
      - alert: SlowDirectoryResponse
        expr: |
          histogram_quantile(
            0.95,
            rate(http_request_duration_seconds_bucket{endpoint=~"/directory.*"}[5m])
          ) > 0.1
        for: 5m
        labels:
          severity: warning
          component: cisco_directory
        annotations:
          summary: "Cisco directory responses are slow"
          description: "Directory XML generation exceeding 100ms target: {{ $value | humanizeDuration }}"
      
      # Sync Failures
      - alert: SyncFailures
        expr: rate(sync_operations_total{status="failure"}[1h]) > 0
        for: 30m
        labels:
          severity: warning
          component: sync
        annotations:
          summary: "Contact sync failures detected"
          description: "{{ $value }} sync failures in the last hour"
      
      # Disk Space
      - alert: LowDiskSpace
        expr: |
          (
            node_filesystem_avail_bytes{mountpoint="/app/data"} 
            / 
            node_filesystem_size_bytes{mountpoint="/app/data"}
          ) < 0.1
        for: 5m
        labels:
          severity: warning
          component: storage
        annotations:
          summary: "Low disk space"
          description: "Less than 10% disk space available in /app/data"
      
      # OAuth Token
      - alert: OAuthNotConfigured
        expr: |
          changes(oauth_token_refreshes_total[24h]) == 0
          and
          time() - process_start_time_seconds > 3600
        for: 1h
        labels:
          severity: warning
          component: oauth
        annotations:
          summary: "OAuth may not be configured"
          description: "No token refreshes in 24 hours, OAuth may need setup"
      
      # Database Size Growth
      - alert: RapidDatabaseGrowth
        expr: |
          (
            database_size_bytes 
            - 
            database_size_bytes offset 1h
          ) > 100000000
        for: 1h
        labels:
          severity: info
          component: database
        annotations:
          summary: "Rapid database growth detected"
          description: "Database grew by {{ $value | humanize1024 }}B in the last hour"
```

### 8. Create Grafana Dashboard

Create `monitoring/grafana/dashboard.json`:

```json
{
  "dashboard": {
    "id": null,
    "uid": "google-contacts-cisco",
    "title": "Google Contacts Cisco Directory",
    "tags": ["contacts", "cisco", "monitoring"],
    "timezone": "browser",
    "schemaVersion": 16,
    "version": 1,
    "refresh": "30s",
    
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [{
          "expr": "rate(http_requests_total[5m])",
          "legendFormat": "{{method}} {{endpoint}}",
          "refId": "A"
        }],
        "yaxes": [{
          "format": "reqps",
          "label": "Requests/sec"
        }]
      },
      {
        "id": 2,
        "title": "Error Rate",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
          "legendFormat": "{{endpoint}} - {{status}}",
          "refId": "A"
        }],
        "alert": {
          "conditions": [{
            "evaluator": {"params": [0.05], "type": "gt"},
            "query": {"params": ["A", "5m", "now"]},
            "type": "query"
          }],
          "name": "High Error Rate Alert"
        }
      },
      {
        "id": 3,
        "title": "Response Time (p95)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p95 - {{endpoint}}",
          "refId": "A"
        }],
        "yaxes": [{
          "format": "s",
          "label": "Duration"
        }]
      },
      {
        "id": 4,
        "title": "Total Contacts",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 8},
        "targets": [{
          "expr": "contacts_total",
          "refId": "A"
        }],
        "options": {
          "colorMode": "value",
          "graphMode": "area"
        }
      },
      {
        "id": 5,
        "title": "Database Size",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 18, "y": 8},
        "targets": [{
          "expr": "database_size_bytes",
          "refId": "A"
        }],
        "fieldConfig": {
          "defaults": {
            "unit": "bytes"
          }
        }
      },
      {
        "id": 6,
        "title": "Sync Success Rate (24h)",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
        "targets": [{
          "expr": "rate(sync_operations_total{status=\"success\"}[24h]) / rate(sync_operations_total[24h])",
          "refId": "A"
        }],
        "fieldConfig": {
          "defaults": {
            "min": 0,
            "max": 1,
            "unit": "percentunit"
          }
        }
      },
      {
        "id": 7,
        "title": "Search Performance",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(search_duration_seconds_bucket[5m]))",
          "legendFormat": "p95",
          "refId": "A"
        }],
        "yaxes": [{
          "format": "s",
          "label": "Duration",
          "max": 0.25
        }]
      }
    ]
  }
}
```

## Verification

After completing this task:

1. **Check Logging Works**:
   ```bash
   # Start application
   uv run python -m google_contacts_cisco.main
   
   # Check logs
   tail -f logs/app.log
   
   # Make some requests
   curl http://localhost:8000/api/contacts
   
   # Check logs show JSON format
   tail -1 logs/app.log | jq
   ```

2. **Check Metrics Endpoint**:
   ```bash
   curl http://localhost:8000/metrics
   
   # Should see Prometheus metrics
   # HELP http_requests_total Total HTTP requests
   # TYPE http_requests_total counter
   # http_requests_total{method="GET",endpoint="/api/contacts",status="200"} 1.0
   ```

3. **Test Health Check**:
   ```bash
   curl http://localhost:8000/health | jq
   
   # Should return detailed health status
   ```

4. **Test Request Tracing**:
   ```bash
   curl -v http://localhost:8000/api/contacts
   
   # Check response headers
   # X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
   # X-Response-Time: 45.23ms
   ```

5. **Set Up Prometheus** (optional):
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'contacts-app'
       static_configs:
         - targets: ['localhost:8000']
       metrics_path: '/metrics'
       scrape_interval: 15s
   ```

6. **Import Grafana Dashboard**:
   - Open Grafana
   - Import `monitoring/grafana/dashboard.json`
   - Verify panels show data

## Notes

- **Structured Logging**: JSON format for easy parsing and aggregation
- **Request IDs**: Unique UUID for tracing requests across logs
- **Metrics**: Prometheus-compatible for standard monitoring tools
- **Health Checks**: Multi-component status for orchestration
- **Log Rotation**: Prevents logs from filling disk
- **Performance**: Minimal overhead (<1% typically)
- **Privacy**: Don't log sensitive data (passwords, tokens)

## Common Issues

1. **Logs Not Appearing**: Check log level, verify handlers configured
2. **Metrics Not Updating**: Ensure MetricsCollector called correctly
3. **High Memory Usage**: Reduce metric cardinality (labels)
4. **Log Disk Full**: Configure log rotation correctly
5. **Prometheus Scrape Fails**: Check /metrics endpoint accessible

## Best Practices

### Logging
- Use appropriate log levels
- Include context (request_id, user_id)
- Don't log sensitive data
- Use structured logging (JSON)
- Log errors with stack traces
- Include timing information

### Metrics
- Keep cardinality low (avoid high-cardinality labels)
- Use appropriate metric types (Counter, Gauge, Histogram)
- Add units to metric names (_seconds, _bytes, _total)
- Document metrics with HELP text
- Use consistent labeling

### Monitoring
- Monitor golden signals (latency, traffic, errors, saturation)
- Set up alerts for critical issues
- Review dashboards regularly
- Track business metrics (contacts, syncs)
- Monitor external dependencies

## Related Documentation

- Prometheus: https://prometheus.io/docs/introduction/overview/
- Grafana: https://grafana.com/docs/grafana/latest/
- python-json-logger: https://github.com/madzak/python-json-logger
- Prometheus Python Client: https://github.com/prometheus/client_python
- Logging Best Practices: https://12factor.net/logs

## Estimated Time

4-5 hours
