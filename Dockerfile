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
    # Default admin credentials (will be overridden by Railway environment variables)
    ADMIN_USERNAME=Mani \
    ADMIN_CODE=ADMIN_MASTER

# Create a non-root user with minimal setup
RUN adduser --disabled-password --gecos "" app_user

# Set working directory
WORKDIR /app

# Create all required directories in one layer
RUN mkdir -p /home/app_user/.streamlit \
             /home/app_user/.cache/yt-dlp \
             /home/app_user/.cache/youtube-dl \
             /app/credentials \
             /app/analysis_temp \
             /app/example_videos \
             /home/app_user/.config/google-chrome

# Install system dependencies and Chrome in a single layer
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
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project first
COPY . .

# Copy specific directories to their locations
COPY .streamlit/config.toml /home/app_user/.streamlit/config.toml

# Set permissions
RUN chown -R app_user:app_user /app /home/app_user && \
    chmod -R 755 /app && \
    chmod -R 777 /app/credentials /app/analysis_temp /app/example_videos /home/app_user/.config /home/app_user/.streamlit /home/app_user/.cache

# Switch to non-root user
USER app_user

# Create an entrypoint script that handles environment variables
RUN echo '#!/bin/bash\n\
# Create directories if they dont exist\n\
mkdir -p /app/credentials\n\
mkdir -p /app/analysis_temp\n\
mkdir -p /app/example_videos\n\
\n\
# Create .env file from environment variables\n\
echo "ADMIN_USERNAME=${ADMIN_USERNAME}" > /app/.env\n\
echo "ADMIN_CODE=${ADMIN_CODE}" >> /app/.env\n\
echo "OPENAI_API_KEY=${OPENAI_API_KEY}" >> /app/.env\n\
echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}" >> /app/.env\n\
echo "GOOGLE_APPLICATION_CREDENTIALS_JSON=${GOOGLE_APPLICATION_CREDENTIALS_JSON}" >> /app/.env\n\
\n\
# Start Streamlit with the PORT from environment\n\
exec streamlit run streamlit_app.py --server.port=${PORT} --server.address=0.0.0.0' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Expose the port from environment variable
EXPOSE ${PORT}

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 