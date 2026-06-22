import os
import sys

# Server socket
bind = os.environ.get("BIND", "0.0.0.0:" + os.environ.get("PORT", "8000"))

# Worker processes
workers = int(os.environ.get("WORKERS", 2))
worker_class = "sync"
timeout = 30

# Logging
accesslog = os.environ.get("ACCESS_LOG", "access.log")
errorlog = os.environ.get("ERROR_LOG", "error.log")
loglevel = os.environ.get("LOG_LEVEL", "info")

# Process naming
proc_name = "sixyao"

# Server mechanics
daemon = False
tmp_upload_dir = None

# SSL (optional)
# certfile = "/path/to/cert.pem"
# keyfile = "/path/to/key.pem"

def on_starting(server):
    """Initialize database on server start."""
    sys.path.insert(0, os.path.dirname(__file__))
    from app import init_db, migrate_db
    init_db()
    migrate_db()
    print("Database initialized.")
