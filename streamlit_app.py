import os
import sys
import logging
from pathlib import Path
import json

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('streamlit_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

try:
    import streamlit as st
    from auth_manager import AuthManager
    
    # Initialize AuthManager
    auth_manager = AuthManager()
    
    # Set page config first
    st.set_page_config(
        page_title="AI Video Commentary Bot",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'remaining_videos' not in st.session_state:
        st.session_state.remaining_videos = 0
    
    def login():
        st.session_state.authenticated = True
        st.session_state.username = st.session_state.get('form_username')
        st.session_state.is_admin = auth_manager.is_admin(st.session_state.username)
        st.rerun()
    
    # Authentication UI
    if not st.session_state.authenticated:
        st.title("🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username", key='form_username')
            code = st.text_input("Access Code", type="password", key='form_code')
            submitted = st.form_submit_button("Login")
            
            if submitted:
                is_valid, message, remaining = auth_manager.validate_user(username, code)
                if is_valid:
                    st.session_state.remaining_videos = remaining
                    st.success(message)
                    login()
                else:
                    st.error(message)
        
        st.markdown("""
        ### How to get access:
        1. Contact the administrator to get an access code
        2. Enter any username you like (this will be your unique identifier)
        3. Enter your access code
        4. Start creating amazing videos!
        """)
        st.stop()
    
    # Show loading message
    loading_placeholder = st.empty()
    loading_placeholder.info("🔄 Initializing application...")
    
    # Admin Interface
    if st.session_state.is_admin:
        with st.sidebar:
            st.subheader("👑 Admin Controls")
            
            # Create new code
            with st.expander("Create New Code"):
                col1, col2 = st.columns(2)
                with col1:
                    prefix = st.text_input("Prefix", value="MK", help="Code prefix (e.g., MK)")
                    max_videos = st.number_input("Max Videos", min_value=1, value=5)
                with col2:
                    num_codes = st.number_input("Number of Codes", min_value=1, max_value=100, value=1)
                    is_admin = st.checkbox("Admin Access")
                
                if st.button("Generate Code(s)"):
                    if num_codes == 1:
                        success, code = auth_manager.create_code(prefix, max_videos, is_admin)
                        if success:
                            st.success(f"Created code: {code}")
                            st.code(code, language=None)  # For easy copying
                        else:
                            st.error("Failed to create code")
                    else:
                        codes = auth_manager.create_bulk_codes(num_codes, max_videos, prefix)
                        if codes:
                            st.success(f"Created {len(codes)} codes")
                            st.code("\n".join(codes), language=None)  # For easy copying
                        else:
                            st.error("Failed to create codes")
            
            # View all codes
            with st.expander("View Codes"):
                codes = auth_manager.get_all_codes()
                for code in codes:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                        **Code:** {code[0]}  
                        Max Videos: {code[1]}  
                        Status: {"🟢 Available" if not code[3] else "🔴 Used"}  
                        Users: {code[4]}  
                        Used: {code[5] or 0}  
                        """)
                    with col2:
                        if code[0] != 'ADMIN_MASTER' and st.button("Delete", key=f"del_{code[0]}"):
                            if auth_manager.delete_code(code[0]):
                                st.success("Code deleted")
                                st.rerun()
            
            # View user statistics
            with st.expander("User Statistics"):
                users = auth_manager.get_user_stats()
                for user in users:
                    st.markdown(f"""
                    **User:** {user[0]}  
                    Code: {user[1]}  
                    Videos Used: {user[2]}/{user[3]}  
                    Last Used: {user[4]}  
                    """)
    
    # Regular user interface
    with st.sidebar:
        st.info(f"""
        👤 **{st.session_state.username}**  
        🎬 Videos remaining: {"∞" if st.session_state.remaining_videos < 0 else st.session_state.remaining_videos}
        """)
        
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.is_admin = False
            st.rerun()
    
    # Continue with the rest of the imports and initialization
    logger.info("✓ Configuration loaded successfully")
    loading_placeholder.success("✓ Configuration loaded successfully")
    
    # Import required modules
    import tempfile
    import asyncio
    import json
    from datetime import datetime
    import shutil
    from telegram.ext import ContextTypes
    from telegram import Bot
    import gc
    import tracemalloc
    import psutil
    
    from new_bot import VideoBot
    from pipeline import Step_1_download_video, Step_7_cleanup
    
    # Initialize VideoBot with proper caching
    @st.cache_resource(show_spinner=False)
    def init_bot():
        """Initialize the VideoBot instance with caching"""
        try:
            return VideoBot()
        except Exception as e:
            logger.error(f"Bot initialization error: {e}")
            raise
    
    # Initialize bot instance
    bot = init_bot()
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
        st.session_state.settings = bot.default_settings.copy()
        st.session_state.is_processing = False
        st.session_state.progress = 0
        st.session_state.status = ""
        st.session_state.initialized = True
    
    # Clear loading message
    loading_placeholder.empty()
    
    # Safe cleanup function
    def cleanup_memory(force=False):
        """Force garbage collection and clear memory"""
        try:
            if force or not st.session_state.get('is_processing', False):
                gc.collect()
                
            # Clear temp directories that are older than 1 hour
            current_time = datetime.now().timestamp()
            for pattern in ['temp_*', 'output_*']:
                for path in Path().glob(pattern):
                    try:
                        if path.is_dir():
                            # Check if directory is older than 1 hour
                            if current_time - path.stat().st_mtime > 3600:
                                shutil.rmtree(path, ignore_errors=True)
                    except Exception as e:
                        logger.warning(f"Failed to remove directory {path}: {e}")
            
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # Custom CSS with mobile responsiveness and centered content
    st.markdown("""
        <style>
        /* Center content and add responsive design */
        .main-content {
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
        }
        
        .stButton>button {
            width: 100%;
            height: 3em;
            margin-top: 1em;
        }
        
        /* Processing animation container */
        .processing-container {
            text-align: center;
            padding: 2rem;
            margin: 2rem auto;
            max-width: 90%;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 1rem;
            backdrop-filter: blur(10px);
        }
        
        /* Telegram-style animations */
        .telegram-animation {
            font-size: 3rem;
            margin: 1rem 0;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        /* Video container */
        .video-container {
            position: relative;
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
            border-radius: 1rem;
            overflow: hidden;
        }
        
        .video-container video {
            width: 100%;
            height: auto;
            border-radius: 1rem;
        }
        
        /* Download button styling */
        .download-btn {
            background: linear-gradient(45deg, #2196F3, #00BCD4);
            color: white;
            padding: 1rem 2rem;
            border-radius: 2rem;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            width: 100%;
            max-width: 300px;
            margin: 1rem auto;
            display: block;
        }
        
        .download-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.2);
        }
        
        /* Mobile optimization */
        @media (max-width: 768px) {
            .main-content {
                padding: 0.5rem;
            }
            
            .processing-container {
                padding: 1rem;
                margin: 1rem auto;
            }
            
            .telegram-animation {
                font-size: 2rem;
            }
        }
        
        /* Status messages */
        .status-message {
            text-align: center;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0.5rem;
            background: rgba(255, 255, 255, 0.1);
        }
        
        /* Progress bar */
        .stProgress > div > div {
            background-color: #2196F3;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Title and description
    st.title("🎬 AI Video Commentary Bot")
    st.markdown("""
        Transform your videos with AI-powered commentary in multiple styles and languages.
        Upload a video or provide a URL to get started!
    """)

    # Add these classes and process_video function before the example videos section
    class StreamlitMessage:
        """Mock Telegram message for status updates"""
        def __init__(self):
            self.message_id = 0
            self.text = ""
            self.video = None
            self.file_id = None
            self.file_name = None
            self.mime_type = None
            self.file_size = None
            self.download_placeholder = st.empty()
            self.video_placeholder = st.empty()
            self.status_placeholder = st.empty()
            self.output_filename = None
            
        async def reply_text(self, text, **kwargs):
            logger.info(f"Status update: {text}")
            self.text = text
            st.session_state.status = text
            self.status_placeholder.markdown(f"🔄 {text}")
            return self
            
        async def edit_text(self, text, **kwargs):
            return await self.reply_text(text)
            
        async def reply_video(self, video, caption=None, **kwargs):
            logger.info("Handling video reply")
            try:
                if hasattr(video, 'read'):
                    video_data = video.read()
                elif isinstance(video, str) and os.path.exists(video):
                    with open(video, "rb") as f:
                        video_data = f.read()
                else:
                    logger.error("Invalid video format")
                    st.error("Invalid video format")
                    return self
                
                self.video_placeholder.video(video_data)
                if caption:
                    st.markdown(f"### {caption}")
                return self
                
            except Exception as e:
                logger.error(f"Error in reply_video: {str(e)}")
                st.error(f"Error displaying video: {str(e)}")
                return self

    class StreamlitUpdate:
        """Mock Telegram Update for bot compatibility"""
        def __init__(self):
            logger.info("Initializing StreamlitUpdate")
            self.effective_user = type('User', (), {'id': 0})
            self.message = StreamlitMessage()
            self.effective_message = self.message

    class StreamlitContext:
        """Mock Telegram context"""
        def __init__(self):
            logger.info("Initializing StreamlitContext")
            self.bot = type('MockBot', (), {
                'get_file': lambda *args, **kwargs: None,
                'send_message': lambda *args, **kwargs: None,
                'edit_message_text': lambda *args, **kwargs: None,
                'send_video': lambda *args, **kwargs: None,
                'send_document': lambda *args, **kwargs: None
            })()
            self.args = []
            self.matches = None
            self.user_data = {}
            self.chat_data = {}
            self.bot_data = {}

    async def process_video():
        # Check if already processing and reset if stuck
        if st.session_state.is_processing:
            # If stuck for more than 5 minutes, reset
            if hasattr(st.session_state, 'processing_start_time'):
                if (datetime.now() - st.session_state.processing_start_time).total_seconds() > 300:
                    st.session_state.is_processing = False
                    logger.warning("Reset stuck processing state")
                else:
                    st.warning("⚠️ Already processing a video. Please wait.")
                    return
            else:
                st.session_state.is_processing = False
        
        try:
            # Set processing start time
            st.session_state.processing_start_time = datetime.now()
            st.session_state.is_processing = True
            
            update = StreamlitUpdate()
            context = StreamlitContext()
            
            # Show processing status
            status_placeholder = st.empty()
            status_placeholder.info("🎬 Starting video processing...")
            
            if 'video_url' in st.session_state and st.session_state.video_url:
                video_url = st.session_state.video_url
                logger.info(f"Processing video URL: {video_url}")
                status_placeholder.info("📥 Downloading video from URL...")
                await bot.process_video_from_url(update, context, video_url)
            elif uploaded_file:
                logger.info(f"Processing uploaded file: {uploaded_file.name}")
                status_placeholder.info("📥 Processing uploaded video...")
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    await bot.process_video_file(update, context, tmp.name, update.message)
            
            status_placeholder.success("✅ Processing complete!")
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            st.error(f"❌ Error processing video: {str(e)}")
        finally:
            # Clear processing state
            st.session_state.is_processing = False
            if hasattr(st.session_state, 'processing_start_time'):
                delattr(st.session_state, 'processing_start_time')
            cleanup_memory(force=True)
    
    # Example Videos Section
    with st.expander("🎥 View Example Videos"):
        st.markdown("### Example Videos")
        st.markdown("Here are some sample videos to demonstrate the capabilities:")
        
        example_videos_dir = Path("example_videos")
        col1, col2 = st.columns(2)
        
        if example_videos_dir.exists():
            videos = list(example_videos_dir.glob("*.mp4"))
            for idx, video_path in enumerate(videos):
                with col1 if idx % 2 == 0 else col2:
                    st.markdown(f"**Example {idx + 1}**")
                    with open(video_path, 'rb') as video_file:
                        st.video(video_file.read())
                    if st.button(f"Process Example {idx + 1}", key=f"example_{idx}"):
                        video_url = f"file://{video_path.absolute()}"
                        st.session_state.video_url = video_url
                        asyncio.run(process_video())
        else:
            st.warning("Example videos directory not found.")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Style selection
        st.subheader("Commentary Style")
        style = st.selectbox(
            "Choose your style",
            options=list(init_bot().styles.keys()),
            format_func=lambda x: f"{init_bot().styles[x]['icon']} {init_bot().styles[x]['name']}",
            key="style"
        )
        st.caption(init_bot().styles[style]['description'])
        
        # AI Model selection
        st.subheader("AI Model")
        llm = st.selectbox(
            "Choose AI model",
            options=list(init_bot().llm_providers.keys()),
            format_func=lambda x: f"{init_bot().llm_providers[x]['icon']} {init_bot().llm_providers[x]['name']}",
            key="llm"
        )
        st.caption(init_bot().llm_providers[llm]['description'])
        
        # Language selection
        st.subheader("Language")
        available_languages = {
            code: info for code, info in init_bot().languages.items()
            if not info.get('requires_openai') or llm == 'openai'
        }
        language = st.selectbox(
            "Choose language",
            options=list(available_languages.keys()),
            format_func=lambda x: f"{init_bot().languages[x]['icon']} {init_bot().languages[x]['name']}",
            key="language"
        )
        
        # Update settings in session state and bot's user settings
        user_id = 0  # Default user ID for Streamlit interface
        init_bot().update_user_setting(user_id, 'style', style)
        init_bot().update_user_setting(user_id, 'llm', llm)
        init_bot().update_user_setting(user_id, 'language', language)
        st.session_state.settings = init_bot().get_user_settings(user_id)
    
    # Main content area
    tab1, tab2 = st.tabs(["📤 Upload Video", "🔗 Video URL"])
    
    # Upload Video Tab
    with tab1:
        uploaded_file = st.file_uploader(
            "Choose a video file",
            type=['mp4', 'mov', 'avi'],
            help="Maximum file size: 50MB"
        )
        
        if uploaded_file:
            if uploaded_file.size > init_bot().MAX_VIDEO_SIZE:
                st.error("❌ Video is too large. Maximum size is 50MB.")
            else:
                st.video(uploaded_file)
                if st.button("Process Video", key="process_upload"):
                    if not st.session_state.is_processing:
                        st.session_state.is_processing = True
                        st.session_state.progress = 0
                        st.session_state.status = "Starting video processing..."
                        try:
                            # Run video processing
                            asyncio.run(process_video())
                        except Exception as e:
                            logger.error(f"Error in process_upload: {str(e)}")
                            st.error("❌ Failed to process video. Please try again.")
                            st.session_state.is_processing = False
                    else:
                        st.warning("⚠️ Already processing a video. Please wait.")
    
    # Video URL Tab
    with tab2:
        video_url = st.text_input(
            "Enter video URL",
            placeholder="https://example.com/video.mp4",
            help="Support for YouTube, Vimeo, TikTok, and more"
        )
        
        if video_url:
            if st.button("Process URL", key="process_url"):
                if not video_url.startswith(('http://', 'https://')):
                    st.error("❌ Please provide a valid URL starting with http:// or https://")
                else:
                    try:
                        # Reset processing state if stuck
                        if st.session_state.is_processing and hasattr(st.session_state, 'processing_start_time'):
                            if (datetime.now() - st.session_state.processing_start_time).total_seconds() > 300:
                                st.session_state.is_processing = False
                                logger.warning("Reset stuck processing state")
                        
                        if not st.session_state.is_processing:
                            st.session_state.progress = 0
                            st.session_state.status = "Starting video processing..."
                            # Run video processing
                            asyncio.run(process_video())
                        else:
                            st.warning("⚠️ Already processing a video. Please wait or refresh the page if stuck.")
                    except Exception as e:
                        logger.error(f"Error in process_url: {str(e)}")
                        st.error("❌ Failed to process video URL. Please try again.")
                        # Reset processing state on error
                        st.session_state.is_processing = False
                        if hasattr(st.session_state, 'processing_start_time'):
                            delattr(st.session_state, 'processing_start_time')
    
    # Add memory monitoring
    if st.sidebar.checkbox("Show Memory Usage"):
        process = psutil.Process()
        memory_info = process.memory_info()
        st.sidebar.write(f"Memory Usage: {memory_info.rss / 1024 / 1024:.2f} MB")
        if st.sidebar.button("Force Cleanup"):
            cleanup_memory()
            st.sidebar.success("Memory cleaned up!")
    
    # Modify the video display section to use st.cache_data
    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def display_video(video_data, caption=None):
        if caption:
            st.markdown(f"### {caption}")
        st.video(video_data)
        return True
    
    # Help section
    with st.expander("ℹ️ Help & Information"):
        st.markdown("""
            ### How to Use
            1. Choose your preferred settings in the sidebar
            2. Upload a video file or provide a video URL
            3. Click the process button and wait for the magic!
            
            ### Features
            - Multiple commentary styles
            - Support for different languages
            - Choice of AI models
            - Professional voice synthesis
            
            ### Limitations
            - Maximum video size: 50MB
            - Maximum duration: 5 minutes
            - Supported formats: MP4, MOV, AVI
            
            ### Need Help?
            If you encounter any issues, try:
            - Using a shorter video
            - Converting your video to MP4 format
            - Checking your internet connection
            - Refreshing the page
        """)
    
    # Before processing a video, check remaining videos
    def check_video_limit():
        if not st.session_state.is_admin and st.session_state.remaining_videos == 0:
            st.error("You have reached your video limit. Please contact the administrator for a new code.")
            return False
        return True
    
    # After successful video processing
    def update_video_usage():
        if not st.session_state.is_admin:
            if auth_manager.increment_usage(st.session_state.username):
                st.session_state.remaining_videos -= 1
            else:
                st.error("Failed to update video usage")
    
except Exception as e:
    logger.error(f"Critical error: {e}", exc_info=True)
    # If streamlit itself fails to import or initialize
    print(f"Critical error: {e}")
    sys.exit(1) 