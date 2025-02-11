# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PORT=8501 \
    HOME=/home/app_user \
    CHROME_BIN=/usr/bin/google-chrome \
    DISPLAY=:99 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Create a non-root user
RUN adduser --disabled-password --gecos "" app_user

# Set working directory
WORKDIR /app

# Create required directories
RUN mkdir -p /home/app_user/.streamlit \
             /home/app_user/.cache/yt-dlp \
             /home/app_user/.cache/youtube-dl \
             /app/credentials \
             /app/analysis_temp \
             /app/example_videos \
             /home/app_user/.config/google-chrome \
             /app/logs

# Install system dependencies (split into multiple RUN commands for better caching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    wget \
    gnupg \
    git \
    libmagic1 \
    libpython3-dev \
    build-essential \
    python3-dev \
    pkg-config \
    sqlite3 \
    procps \
    netcat \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome (in a separate RUN command)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && google-chrome --version

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project
COPY . .

# Copy Streamlit config
COPY .streamlit/config.toml /home/app_user/.streamlit/config.toml

# Set permissions
RUN chown -R app_user:app_user /app /home/app_user && \
    chmod -R 755 /app && \
    chmod -R 777 /app/credentials /app/analysis_temp /app/example_videos /app/logs /home/app_user/.config /home/app_user/.streamlit /home/app_user/.cache

# Create healthcheck script
RUN echo '#!/bin/bash\n\
nc -z localhost ${PORT} || exit 1\n\
curl -f http://localhost:${PORT}/_stcore/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "[$(date)] Starting container setup..."\n\
\n\
log() {\n\
    echo "[$(date)] $1"\n\
}\n\
\n\
# Create and set up directories\n\
log "Setting up directories..."\n\
for dir in /app/logs /app/credentials /app/analysis_temp /app/example_videos; do\n\
    mkdir -p $dir\n\
    chown -R app_user:app_user $dir\n\
    chmod -R 777 $dir\n\
done\n\
\n\
# Set up logging\n\
log "Setting up logging..."\n\
touch /app/logs/app.log\n\
chmod 666 /app/logs/app.log\n\
\n\
# Initialize database\n\
log "Initializing database..."\n\
if [ ! -f /app/credentials/auth.db ]; then\n\
    sqlite3 /app/credentials/auth.db "PRAGMA journal_mode=WAL;"\n\
    chown app_user:app_user /app/credentials/auth.db*\n\
    chmod 666 /app/credentials/auth.db*\n\
fi\n\
\n\
# Create .env file\n\
log "Creating .env file..."\n\
cat > /app/.env << EOL\n\
ADMIN_USERNAME=${ADMIN_USERNAME:-Mani}\n\
ADMIN_CODE=${ADMIN_CODE:-Manigujjar01!}\n\
OPENAI_API_KEY=${OPENAI_API_KEY}\n\
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}\n\
GOOGLE_APPLICATION_CREDENTIALS_JSON=${GOOGLE_APPLICATION_CREDENTIALS_JSON}\n\
CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME}\n\
CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY}\n\
CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET}\n\
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}\n\
EOL\n\
\n\
# Check if critical environment variables are set\n\
log "Checking environment variables..."\n\
for var in OPENAI_API_KEY GOOGLE_APPLICATION_CREDENTIALS_JSON; do\n\
    if [ -z "${!var}" ]; then\n\
        log "Warning: $var is not set"\n\
    fi\n\
done\n\
\n\
# Start Streamlit\n\
log "Starting Streamlit..."\n\
exec streamlit run streamlit_app.py \\\n\
    --server.port=${PORT} \\\n\
    --server.address=0.0.0.0 \\\n\
    --server.maxUploadSize=50 \\\n\
    --server.enableXsrfProtection=false \\\n\
    --server.enableCORS=true \\\n\
    --server.headless=true \\\n\
    --server.enableWebsocketCompression=false \\\n\
    --server.enableStaticServing=true \\\n\
    --logger.level=debug \\\n\
    --logger.messageFormat="%(asctime)s %(levelname)s: %(message)s" \\\n\
    2>&1 | tee -a /app/logs/app.log' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER app_user

# Expose port
EXPOSE ${PORT}

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=180s --retries=3 \
    CMD /app/healthcheck.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 