# AI Video Commentary Bot

A powerful application that adds AI-generated commentary to videos using multiple styles and languages. Available both as a Telegram bot and a Streamlit web application.

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Git
- Docker (optional)
- API Keys:
  - OpenAI API key
  - Deepseek API key
  - Google Cloud credentials (for Text-to-Speech)
  - Telegram Bot Token (for Telegram bot)

### Local Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

3. Edit the `.env` file with your API keys and credentials.

4. Start the application:
```bash
streamlit run streamlit_app.py
```

### Docker Setup

1. Build the Docker image:
```bash
docker build -t video-commentary-bot .
```

2. Run the container:
```bash
docker run -p 8501:8501 \
  --env-file .env \
  video-commentary-bot
```

### Railway Deployment

1. Fork this repository
2. Create a new project on [Railway](https://railway.app/)
3. Connect your GitHub repository
4. Add environment variables in Railway:
   - `OPENAI_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - Other variables from `.env.example`
5. Deploy!

## 📝 Configuration

### Environment Variables

Copy `.env.example` to `.env` and fill in:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DEEPSEEK_API_KEY`: Your Deepseek API key
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Your Google Cloud credentials JSON
- `ADMIN_USERNAME`: Admin username
- `ADMIN_CODE`: Admin access code

### Streamlit Configuration

The `.streamlit/config.toml` file contains Streamlit-specific settings:
- Server configuration
- Theme customization
- Logging settings

## 🎯 Features

- 🎭 Multiple commentary styles:
  - Documentary
  - Energetic
  - Analytical
  - Storyteller
- 🤖 Choice of AI models:
  - OpenAI GPT-4
  - Deepseek
- 🌐 Multiple language support:
  - English
  - Urdu
- 🎙️ Professional voice synthesis
- 📤 Support for video upload and URL processing
- 🎬 Support for various video platforms

## 📋 Project Structure

```
.
├── .streamlit/          # Streamlit configuration
├── credentials/         # API credentials and database
├── example_videos/      # Sample videos
├── pipeline/           # Video processing pipeline
│   ├── Step_1_download_video.py
│   ├── Step_2_extract_frames.py
│   ├── Step_3_analyze_frames.py
│   ├── Step_4_generate_commentary.py
│   ├── Step_5_generate_audio.py
│   ├── Step_6_video_generation.py
│   └── Step_7_cleanup.py
├── streamlit_app.py    # Web interface
├── new_bot.py         # Telegram bot
├── auth_manager.py    # Authentication system
├── Dockerfile         # Container configuration
└── requirements.txt   # Python dependencies
```

## ⚠️ Limitations

- Maximum video size: 50MB
- Maximum video duration: 5 minutes
- Supported formats: MP4, MOV, AVI

## 🔧 Troubleshooting

### Common Issues

1. **Build Errors**
   ```bash
   # Clear Docker cache
   docker builder prune
   # Rebuild image
   docker build --no-cache -t video-commentary-bot .
   ```

2. **Permission Issues**
   ```bash
   # Fix permissions
   chmod -R 755 .
   chmod -R 777 credentials analysis_temp example_videos logs
   ```

3. **Database Issues**
   ```bash
   # Reinitialize database
   rm credentials/auth.db
   sqlite3 credentials/auth.db "PRAGMA journal_mode=WAL;"
   ```

4. **Memory Issues**
   - Increase Docker memory limit
   - Clear temporary files: `rm -rf temp_* analysis_*`

### Logs

- Application logs: `logs/app.log`
- Streamlit logs: `~/.streamlit/logs/`

## 🔒 Security

- All API keys stored in `.env`
- Database access restricted
- Non-root Docker user
- CORS and XSRF protection

## 📦 Updates

1. Pull latest changes:
```bash
git pull origin main
```

2. Update dependencies:
```bash
pip install -r requirements.txt --upgrade
```

3. Rebuild Docker image:
```bash
docker build -t video-commentary-bot .
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Latest Updates

- ✨ Added Telegram-style animations during video processing
- 🎨 Improved mobile-responsive UI design
- 🚀 Optimized video processing and cleanup
- 💾 Instant video availability after processing
- 🔄 Automatic cleanup of temporary files
- 📱 Enhanced mobile viewing experience

## 🚀 Quick Deploy to Railway

1. Fork this repository to your GitHub account
2. Create a new project on [Railway](https://railway.app/)
3. Connect your GitHub repository to Railway
4. Add the following environment variables in Railway:
   - `OPENAI_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON` (entire JSON content)
   - Other variables from `.env.example`
5. Deploy! Railway will automatically build and deploy your app

Your app will be available at: `https://your-project-name.railway.app`

## 🛠️ Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Deepseek API key
- Google Cloud credentials (for Text-to-Speech)
- Telegram Bot Token (for Telegram bot only)

## 📦 Installation

1. Clone the repository:
   ```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
Copy `.env.example` to `.env` and fill in your values:
   ```bash
cp .env.example .env
```

4. Set up configuration:
Copy `railway.json.example` to `railway.json` and update with your credentials:
```bash
cp railway.json.example railway.json
```

## 🚀 Running the Applications

### Streamlit Web App
```bash
streamlit run streamlit_app.py
```
The web interface will be available at `http://localhost:8501`

### Telegram Bot
```bash
python new_bot.py
```

## 💡 Usage

### Web Interface
1. Open the Streamlit app in your browser
2. Choose your preferred settings in the sidebar:
   - Commentary style
   - AI model
   - Language
3. Either upload a video file or provide a video URL
4. Click "Process" and watch the Telegram-style animations
5. Download your enhanced video when processing is complete

### Telegram Bot
1. Start a chat with the bot
2. Use /start to see available commands
3. Configure your preferences using /settings
4. Send a video file or URL to process
5. Wait for the bot to return your enhanced video

## 🔗 Share Your App

After deploying to Railway, you can share your app using the Railway-provided URL:
`https://your-project-name.railway.app`

To customize the domain:
1. Go to your Railway project settings
2. Navigate to the "Domains" section
3. Add a custom domain or use Railway's provided domain

Remember to secure your API keys and credentials when sharing the app! 