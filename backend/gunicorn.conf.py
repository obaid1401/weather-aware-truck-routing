"""Gunicorn settings for the production server (used by the Docker image).

The port comes from the environment: Render sets PORT automatically, and a local container
must be given one (for example `-e PORT=8000`). Startup fails clearly if it is missing.

The sizing below suits this application. It can be overridden without a code change through
Gunicorn's own GUNICORN_CMD_ARGS variable, for example GUNICORN_CMD_ARGS="--workers 1".
"""

import os

_port = os.environ.get("PORT", "").strip()
if not _port.isdigit():
    raise RuntimeError(
        "PORT is not set to a port number. Render sets it automatically; "
        "for a local container pass -e PORT=8000."
    )

bind = f"0.0.0.0:{_port}"

# An analysis waits on several external providers: usually 10 to 20 seconds, up to about 90.
# Threads let a worker keep answering health checks and other requests meanwhile.
worker_class = "gthread"
workers = 2
threads = 4

# Longer than the frontend's 90-second request timeout, so an analysis is never cut short here.
timeout = 120
graceful_timeout = 30

# Log to stdout and stderr, where the hosting platform collects them.
accesslog = "-"
errorlog = "-"
