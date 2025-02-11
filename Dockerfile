# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Set timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies in a single RUN command to reduce layers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        ffmpeg \
        libsm6 \
        libxext6 \
        libgl1-mesa-glx \
        file \
        libmagic1 \
        sqlite3 \
        ca-certificates \
        wget \
        gnupg \
        lsb-release \
        python3-dev \
        pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# Create app directory
WORKDIR /app

# Create non-root user
RUN groupadd -r streamlit && \
    useradd -r -g streamlit -s /bin/bash -d /home/streamlit streamlit && \
    mkdir -p /home/streamlit && \
    chown -R streamlit:streamlit /home/streamlit

# Create and set permissions for required directories
RUN mkdir -p /app/credentials \
             /app/analysis_temp \
             /app/example_videos \
             /app/logs \
             /app/temp \
             /home/streamlit/.streamlit \
             /home/streamlit/.cache && \
    chown -R streamlit:streamlit /app /home/streamlit

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Set permissions
RUN chown -R streamlit:streamlit /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/credentials /app/analysis_temp /app/example_videos /app/logs /app/temp

# Create necessary files and set permissions
RUN touch /app/logs/app.log && \
    chown streamlit:streamlit /app/logs/app.log && \
    chmod 666 /app/logs/app.log

# Initialize SQLite database
RUN mkdir -p /app/credentials && \
    sqlite3 /app/credentials/auth.db "PRAGMA journal_mode=WAL;" && \
    chown -R streamlit:streamlit /app/credentials && \
    chmod 666 /app/credentials/auth.db*

# Create entrypoint script
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'set -e' >> /app/entrypoint.sh && \
    echo 'log() { echo "[$(date)] $1"; }' >> /app/entrypoint.sh && \
    echo 'log "Checking environment variables..."' >> /app/entrypoint.sh && \
    echo 'required_vars=("OPENAI_API_KEY" "DEEPSEEK_API_KEY" "GOOGLE_APPLICATION_CREDENTIALS_JSON")' >> /app/entrypoint.sh && \
    echo 'for var in "${required_vars[@]}"; do' >> /app/entrypoint.sh && \
    echo '    if [ -z "${!var}" ]; then' >> /app/entrypoint.sh && \
    echo '        log "Error: $var is not set"' >> /app/entrypoint.sh && \
    echo '        exit 1' >> /app/entrypoint.sh && \
    echo '    fi' >> /app/entrypoint.sh && \
    echo 'done' >> /app/entrypoint.sh && \
    echo 'if [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS_JSON" ]; then' >> /app/entrypoint.sh && \
    echo '    log "Setting up Google credentials..."' >> /app/entrypoint.sh && \
    echo '    echo "$GOOGLE_APPLICATION_CREDENTIALS_JSON" > /app/credentials/google_credentials.json' >> /app/entrypoint.sh && \
    echo '    export GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google_credentials.json' >> /app/entrypoint.sh && \
    echo 'fi' >> /app/entrypoint.sh && \
    echo 'log "Starting Streamlit..."' >> /app/entrypoint.sh && \
    echo 'exec streamlit run streamlit_app.py --server.port=${PORT} --server.address=0.0.0.0 --server.maxUploadSize=50 --server.enableXsrfProtection=false --server.enableCORS=true --server.headless=true --server.enableWebsocketCompression=false --server.enableStaticServing=true' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER streamlit

# Copy Streamlit config
COPY .streamlit/config.toml /home/streamlit/.streamlit/config.toml

# Expose port
EXPOSE ${PORT}

# Healthcheck using curl
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 