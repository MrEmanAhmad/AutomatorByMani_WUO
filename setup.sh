#!/bin/bash

# Function for logging
log() {
    echo "[$(date)] $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
log "Checking Python version..."
if ! command_exists python3; then
    log "Error: Python 3 is not installed"
    exit 1
fi

python3 --version

# Check if pip is installed
log "Checking pip installation..."
if ! command_exists pip3; then
    log "Error: pip3 is not installed"
    exit 1
fi

# Create virtual environment
log "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
log "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
log "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
log "Creating necessary directories..."
mkdir -p credentials
mkdir -p analysis_temp
mkdir -p example_videos
mkdir -p logs
mkdir -p temp

# Check for .env file
log "Checking environment setup..."
if [ ! -f .env ]; then
    log "Creating .env file..."
    cp .env.example .env
    log "Please edit .env file with your credentials"
fi

# Initialize SQLite database
log "Initializing database..."
if [ ! -f credentials/auth.db ]; then
    sqlite3 credentials/auth.db "PRAGMA journal_mode=WAL;"
fi

# Set file permissions
log "Setting file permissions..."
chmod -R 755 .
chmod -R 777 credentials analysis_temp example_videos logs temp
chmod 666 credentials/auth.db*

# Create log file
log "Setting up logging..."
touch logs/app.log
chmod 666 logs/app.log

# Check for required environment variables
log "Checking required environment variables..."
required_vars=("OPENAI_API_KEY" "DEEPSEEK_API_KEY" "GOOGLE_APPLICATION_CREDENTIALS_JSON")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    log "Warning: The following required environment variables are not set:"
    printf '%s\n' "${missing_vars[@]}"
    log "Please set them in your .env file"
fi

# Setup complete
log "Setup complete! You can now run the application with:"
echo "streamlit run streamlit_app.py" 