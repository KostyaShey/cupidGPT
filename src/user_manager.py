import logging
from typing import Dict, Any, Optional
from database import DatabaseManager


class UserManager:
    """Manages user registration, authentication, and pairing."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def register_user(self, telegram_id: int, username: str = None, 
                     first_name: str = None, last_name: str = None) -> bool:
        """Register a new user or update existing user info."""
        try:
            success = self.db.add_user(telegram_id, username, first_name, last_name)
            if success:
                logging.info(f"User registered: {telegram_id} (@{username})")
            return success
        except Exception as e:
            logging.error(f"Error registering user {telegram_id}: {e}")
            return False
    
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by Telegram ID."""
        return self.db.get_user_by_telegram_id(telegram_id)
    
    def is_user_registered(self, telegram_id: int) -> bool:
        """Check if a user is registered."""
        user = self.get_user(telegram_id)
        return user is not None
    
    def is_user_paired(self, telegram_id: int) -> bool:
        """Check if a user is paired with another user."""
        user = self.get_user(telegram_id)
        return user is not None and user.get('paired_user_id') is not None
    
    def get_paired_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get the paired user for a given user."""
        return self.db.get_paired_user(telegram_id)
    
    async def pair_users(self, user1_telegram_id: int, partner_username: str) -> Dict[str, Any]:
        """Pair two users together."""
        try:
            # Check if user1 is registered
            user1 = self.get_user(user1_telegram_id)
            if not user1:
                return {
                    'success': False,
                    'message': "You need to start the bot first with /start"
                }
            
            # Check if user1 is already paired
            if self.is_user_paired(user1_telegram_id):
                paired_user = self.get_paired_user(user1_telegram_id)
                return {
                    'success': False,
                    'message': f"You are already paired with {paired_user.get('first_name', 'someone')} (@{paired_user.get('username', 'unknown')})"
                }
            
            # Find user2 by username
            user2 = self._find_user_by_username(partner_username)
            if not user2:
                return {
                    'success': False,
                    'message': f"User @{partner_username} not found. They need to start the bot first with /start"
                }
            
            # Check if user2 is already paired
            if self.is_user_paired(user2['telegram_id']):
                return {
                    'success': False,
                    'message': f"@{partner_username} is already paired with someone else"
                }
            
            # Check if trying to pair with themselves
            if user1_telegram_id == user2['telegram_id']:
                return {
                    'success': False,
                    'message': "You cannot pair with yourself!"
                }
            
            # Pair the users
            success = self.db.pair_users(user1_telegram_id, user2['telegram_id'])
            
            if success:
                logging.info(f"Users paired: {user1_telegram_id} with {user2['telegram_id']}")
                return {
                    'success': True,
                    'message': f"Successfully paired with @{partner_username}! You can now create shared appointments and checklists."
                }
            else:
                return {
                    'success': False,
                    'message': "Failed to pair users. Please try again."
                }
                
        except Exception as e:
            logging.error(f"Error pairing users: {e}")
            return {
                'success': False,
                'message': "An error occurred while pairing. Please try again."
            }
    
    def _find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find a user by their username."""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"Error finding user by username: {e}")
            return None
    
    def get_user_status(self, telegram_id: int) -> str:
        """Get user's current status."""
        user = self.get_user(telegram_id)
        if not user:
            return "❌ You are not registered. Use /start to register."
        
        status = f"👤 *User Status*\n\n"
        status += f"Name: {user.get('first_name', 'N/A')} {user.get('last_name', '')}\n"
        status += f"Username: @{user.get('username', 'N/A')}\n"
        
        if self.is_user_paired(telegram_id):
            paired_user = self.get_paired_user(telegram_id)
            status += f"✅ Paired with: {paired_user.get('first_name', 'N/A')} (@{paired_user.get('username', 'N/A')})\n"
        else:
            status += "❌ Not paired. Use `/pair @username` to pair with your partner.\n"
        
        return status
    
    def unpair_user(self, telegram_id: int) -> bool:
        """Unpair a user from their partner."""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current user and their paired user
                user = self.get_user(telegram_id)
                if not user or not user.get('paired_user_id'):
                    return False
                
                user_id = user['id']
                paired_user_id = user['paired_user_id']
                
                # Unpair both users
                cursor.execute("UPDATE users SET paired_user_id = NULL WHERE id = ?", (user_id,))
                cursor.execute("UPDATE users SET paired_user_id = NULL WHERE id = ?", (paired_user_id,))
                
                conn.commit()
                logging.info(f"Users unpaired: {user_id} and {paired_user_id}")
                return True
                
        except Exception as e:
            logging.error(f"Error unpairing user: {e}")
            return False
    
    def get_all_users(self) -> list:
        """Get all registered users (for admin purposes)."""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return []
    
    def get_user_count(self) -> int:
        """Get total number of registered users."""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting user count: {e}")
            return 0
    
    def get_paired_users_count(self) -> int:
        """Get number of paired users."""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE paired_user_id IS NOT NULL")
                return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting paired users count: {e}")
            return 0