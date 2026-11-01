# Production image for the Django API, for Render or any container host.
# All configuration (secrets included) comes from the environment at run time: nothing is
# baked into the image, and .env is excluded by .dockerignore.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Tolerate slow or unreliable networks while downloading packages.
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

WORKDIR /app

# Runtime dependencies only, installed before the code so code changes reuse this layer.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user. Gunicorn keeps its control socket in the home directory.
RUN useradd --system --uid 10001 --create-home app
USER app

# Gunicorn binds to the PORT environment variable (see gunicorn.conf.py).
CMD ["gunicorn", "--config", "gunicorn.conf.py", "config.wsgi:application"]
