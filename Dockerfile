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

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# Copy dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Install locked dependencies into the venv
# --frozen: fail if lockfile and pyproject disagree
# --no-dev: don’t install dev extras
RUN uv sync --frozen --no-dev

COPY . .

COPY ./entrypoint.sh /
ENTRYPOINT ["sh", "/entrypoint.sh"]
