import sqlite3
import os
from datetime import datetime
import logging
from pathlib import Path
import random
import string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get admin credentials from environment variables
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'Mani')  # Fallback for development
ADMIN_CODE = os.getenv('ADMIN_CODE', 'ADMIN_MASTER')  # Fallback for development

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.db_path = Path("credentials/auth.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Initialize the SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create codes table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS codes (
                    code TEXT PRIMARY KEY,
                    max_videos INTEGER NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    is_used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Create users table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    videos_used INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    FOREIGN KEY (code) REFERENCES codes(code)
                )
                ''')
                
                # Create default admin code if not exists
                cursor.execute('INSERT OR IGNORE INTO codes (code, max_videos, is_admin) VALUES (?, ?, ?)',
                             (ADMIN_CODE, -1, 1))
                
                # Create default admin user if not exists
                cursor.execute('INSERT OR IGNORE INTO users (username, code, videos_used, last_used) VALUES (?, ?, ?, ?)',
                             (ADMIN_USERNAME, ADMIN_CODE, 0, datetime.now()))
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def generate_unique_code(self, prefix: str = "MK") -> str:
        """Generate a unique random code with the given prefix."""
        while True:
            # Generate 6 random alphanumeric characters
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code = f"{prefix}_{random_part}"
            
            # Check if code exists
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM codes WHERE code = ?', (code,))
                if not cursor.fetchone():
                    return code
    
    def create_bulk_codes(self, num_codes: int, max_videos: int, prefix: str = "MK") -> list:
        """Create multiple unique codes with the same video limit."""
        created_codes = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for _ in range(num_codes):
                    code = self.generate_unique_code(prefix)
                    cursor.execute(
                        'INSERT INTO codes (code, max_videos, is_admin) VALUES (?, ?, ?)',
                        (code, max_videos, False)
                    )
                    created_codes.append(code)
                conn.commit()
            return created_codes
        except Exception as e:
            logger.error(f"Error creating bulk codes: {e}")
            return []
    
    def validate_user(self, username: str, code: str) -> tuple[bool, str, int]:
        """
        Validate user credentials and return (is_valid, message, remaining_videos).
        For admin users, remaining_videos will be -1.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if code exists and is not used (except for admin code)
                cursor.execute('''
                SELECT max_videos, is_admin, is_used 
                FROM codes 
                WHERE code = ?
                ''', (code,))
                code_info = cursor.fetchone()
                
                if not code_info:
                    return False, "Invalid code", 0
                
                max_videos, is_admin, is_used = code_info
                
                # Check if username exists
                cursor.execute('SELECT code, videos_used FROM users WHERE username = ?', (username,))
                user_info = cursor.fetchone()
                
                if user_info:
                    user_code, videos_used = user_info
                    if user_code != code:
                        return False, "Username already registered with a different code", 0
                    if not is_admin and videos_used >= max_videos:
                        return False, "Video limit exceeded", 0
                    return True, "Welcome back!", max_videos - videos_used if max_videos > 0 else -1
                
                # For non-admin codes, check if code is already used
                if not is_admin and is_used:
                    return False, "This code has already been used", 0
                
                # New user - register them
                cursor.execute(
                    'INSERT INTO users (username, code, videos_used, last_used) VALUES (?, ?, 0, ?)',
                    (username, code, datetime.now())
                )
                
                # Mark code as used for non-admin codes
                if not is_admin:
                    cursor.execute('UPDATE codes SET is_used = 1 WHERE code = ?', (code,))
                
                conn.commit()
                return True, "Welcome new user!", max_videos if max_videos > 0 else -1
                
        except Exception as e:
            logger.error(f"User validation error: {e}")
            return False, f"Authentication error: {str(e)}", 0
    
    def increment_usage(self, username: str) -> bool:
        """Increment the video usage count for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE users 
                SET videos_used = videos_used + 1,
                    last_used = CURRENT_TIMESTAMP
                WHERE username = ?
                ''', (username,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
            return False
    
    def is_admin(self, username: str) -> bool:
        """Check if a user has admin privileges."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT c.is_admin 
                FROM users u
                JOIN codes c ON u.code = c.code
                WHERE u.username = ?
                ''', (username,))
                result = cursor.fetchone()
                return bool(result and result[0])
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
    
    def create_code(self, prefix: str, max_videos: int, is_admin: bool = False) -> tuple[bool, str]:
        """Create a new code with random generation."""
        try:
            code = self.generate_unique_code(prefix)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO codes (code, max_videos, is_admin) VALUES (?, ?, ?)',
                    (code, max_videos, is_admin)
                )
                conn.commit()
                return True, code
        except sqlite3.IntegrityError:
            return False, ""
        except Exception as e:
            logger.error(f"Error creating code: {e}")
            return False, ""
    
    def delete_code(self, code: str) -> bool:
        """Delete a code and its associated users (admin only)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # First delete associated users
                cursor.execute('DELETE FROM users WHERE code = ?', (code,))
                # Then delete the code
                cursor.execute('DELETE FROM codes WHERE code = ?', (code,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting code: {e}")
            return False
    
    def get_all_codes(self) -> list:
        """Get all codes and their usage (admin only)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    c.code,
                    c.max_videos,
                    c.is_admin,
                    c.is_used,
                    COUNT(u.username) as user_count,
                    SUM(u.videos_used) as total_videos_used,
                    c.created_at
                FROM codes c
                LEFT JOIN users u ON c.code = u.code
                GROUP BY c.code
                ''')
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting codes: {e}")
            return []
    
    def get_user_stats(self, code: str = None) -> list:
        """Get user statistics, optionally filtered by code (admin only)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = '''
                SELECT 
                    u.username,
                    u.code,
                    u.videos_used,
                    c.max_videos,
                    u.last_used
                FROM users u
                JOIN codes c ON u.code = c.code
                '''
                params = ()
                if code:
                    query += ' WHERE u.code = ?'
                    params = (code,)
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return [] 