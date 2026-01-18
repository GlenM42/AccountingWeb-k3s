FROM python:3.12-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE=1 : prevents Python from creating .pyc files in __pycache__/
# PYTHONUNBUFFERED=1        : forces Python to flush stdout/stderr immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies required for mysqlclient
# "apt-get clean"               : removes downloaded .deb package files; they're only needed for the install
# "rm -rf /var/lib/apt/lists/*" : removes package index files gotten by `apt-get update`
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv to /usr/local/bin (accessible to all users)
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# Create non-root user and group (UID/GID 1000)
RUN groupadd -g 1000 django && \
    useradd -u 1000 -g django -m -s /bin/bash django

# Copy dependency files first (better caching)
# Use --chown to avoid creating duplicate layer
COPY --chown=django:django pyproject.toml uv.lock ./

# Install locked dependencies into the venv
# --frozen: fail if lockfile and pyproject disagree
# --no-dev: don't install dev extras
RUN uv sync --frozen --no-dev

# Copy application code with proper ownership
# CRITICAL: Use --chown during COPY to avoid file duplication
# Using chown after COPY creates a new layer that duplicates all files (~160MB waste)
COPY --chown=django:django . .

# Create staticfiles directory and make entrypoint executable
# Only change permissions on files that need it, not entire /app
RUN mkdir -p /app/staticfiles && \
    chown django:django /app/staticfiles && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user for runtime
USER django

# Document exposed port
EXPOSE 8000

# Run entrypoint as non-root user
ENTRYPOINT ["/app/entrypoint.sh"]
