import sqlite3
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseManager:
    """Manages SQLite database operations for the CupidGPT bot."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        paired_user_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (paired_user_id) REFERENCES users (id)
                    )
                """)
                
                # Appointments table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        appointment_date TIMESTAMP NOT NULL,
                        location TEXT,
                        created_by INTEGER NOT NULL,
                        shared_with INTEGER,
                        reminder_sent BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users (id),
                        FOREIGN KEY (shared_with) REFERENCES users (id)
                    )
                """)
                
                # Checklists table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checklists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        created_by INTEGER NOT NULL,
                        shared_with INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users (id),
                        FOREIGN KEY (shared_with) REFERENCES users (id)
                    )
                """)
                
                # Checklist items table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checklist_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        checklist_id INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        completed BOOLEAN DEFAULT FALSE,
                        completed_by INTEGER,
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (checklist_id) REFERENCES checklists (id) ON DELETE CASCADE,
                        FOREIGN KEY (completed_by) REFERENCES users (id)
                    )
                """)
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def add_user(self, telegram_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None) -> bool:
        """Add a new user to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, try to insert the user (will be ignored if telegram_id already exists)
                cursor.execute("""
                    INSERT OR IGNORE INTO users 
                    (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (telegram_id, username, first_name, last_name))
                
                # Then update the user information to keep it current
                # This preserves the original ID while updating other fields
                cursor.execute("""
                    UPDATE users 
                    SET username = ?, first_name = ?, last_name = ?
                    WHERE telegram_id = ?
                """, (username, first_name, last_name, telegram_id))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error adding user: {e}")
            return False
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"Error getting user: {e}")
            return None
    
    def pair_users(self, user1_telegram_id: int, user2_telegram_id: int) -> bool:
        """Pair two users together."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user IDs
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user1_telegram_id,))
                user1_id = cursor.fetchone()
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user2_telegram_id,))
                user2_id = cursor.fetchone()
                
                if not user1_id or not user2_id:
                    return False
                
                user1_id = user1_id[0]
                user2_id = user2_id[0]
                
                # Pair the users
                cursor.execute("UPDATE users SET paired_user_id = ? WHERE id = ?", (user2_id, user1_id))
                cursor.execute("UPDATE users SET paired_user_id = ? WHERE id = ?", (user1_id, user2_id))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error pairing users: {e}")
            return False
    
    def get_paired_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get the paired user for a given user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u2.* FROM users u1
                    JOIN users u2 ON u1.paired_user_id = u2.id
                    WHERE u1.telegram_id = ?
                """, (telegram_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"Error getting paired user: {e}")
            return None
    
    def create_appointment(self, title: str, description: str, appointment_date: datetime,
                          location: str, created_by_telegram_id: int) -> Optional[int]:
        """Create a new appointment."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user ID and paired user ID
                cursor.execute("SELECT id, paired_user_id FROM users WHERE telegram_id = ?", 
                             (created_by_telegram_id,))
                result = cursor.fetchone()
                if not result:
                    return None
                
                created_by_id, shared_with_id = result
                
                cursor.execute("""
                    INSERT INTO appointments 
                    (title, description, appointment_date, location, created_by, shared_with)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (title, description, appointment_date, location, created_by_id, shared_with_id))
                
                appointment_id = cursor.lastrowid
                conn.commit()
                return appointment_id
        except sqlite3.Error as e:
            logging.error(f"Error creating appointment: {e}")
            return None
    
    def get_appointments(self, telegram_id: int, upcoming_only: bool = True) -> List[Dict[str, Any]]:
        """Get appointments for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get user ID
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
                user_result = cursor.fetchone()
                if not user_result:
                    return []
                
                user_id = user_result[0]
                
                query = """
                    SELECT a.*, u.first_name as creator_name
                    FROM appointments a
                    JOIN users u ON a.created_by = u.id
                    WHERE (a.created_by = ? OR a.shared_with = ?)
                """
                params = [user_id, user_id]
                
                if upcoming_only:
                    query += " AND a.appointment_date >= datetime('now')"
                
                query += " ORDER BY a.appointment_date ASC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Error getting appointments: {e}")
            return []
    
    def create_checklist(self, title: str, description: str, 
                        created_by_telegram_id: int) -> Optional[int]:
        """Create a new checklist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user ID and paired user ID
                cursor.execute("SELECT id, paired_user_id FROM users WHERE telegram_id = ?", 
                             (created_by_telegram_id,))
                result = cursor.fetchone()
                if not result:
                    return None
                
                created_by_id, shared_with_id = result
                
                cursor.execute("""
                    INSERT INTO checklists (title, description, created_by, shared_with)
                    VALUES (?, ?, ?, ?)
                """, (title, description, created_by_id, shared_with_id))
                
                checklist_id = cursor.lastrowid
                conn.commit()
                return checklist_id
        except sqlite3.Error as e:
            logging.error(f"Error creating checklist: {e}")
            return None
    
    def add_checklist_item(self, checklist_id: int, text: str) -> bool:
        """Add an item to a checklist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO checklist_items (checklist_id, text)
                    VALUES (?, ?)
                """, (checklist_id, text))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error adding checklist item: {e}")
            return False
    
    def get_checklists(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Get checklists for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get user ID
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
                user_result = cursor.fetchone()
                if not user_result:
                    return []
                
                user_id = user_result[0]
                
                cursor.execute("""
                    SELECT c.*, u.first_name as creator_name
                    FROM checklists c
                    JOIN users u ON c.created_by = u.id
                    WHERE (c.created_by = ? OR c.shared_with = ?)
                    ORDER BY c.created_at DESC
                """, (user_id, user_id))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Error getting checklists: {e}")
            return []
    
    def get_checklist_items(self, checklist_id: int) -> List[Dict[str, Any]]:
        """Get items for a checklist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ci.*, u.first_name as completed_by_name
                    FROM checklist_items ci
                    LEFT JOIN users u ON ci.completed_by = u.id
                    WHERE ci.checklist_id = ?
                    ORDER BY ci.created_at ASC
                """, (checklist_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Error getting checklist items: {e}")
            return []
    
    def toggle_checklist_item(self, item_id: int, telegram_id: int) -> bool:
        """Toggle completion status of a checklist item."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user ID
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
                user_result = cursor.fetchone()
                if not user_result:
                    return False
                
                user_id = user_result[0]
                
                # Get current status
                cursor.execute("SELECT completed FROM checklist_items WHERE id = ?", (item_id,))
                result = cursor.fetchone()
                if not result:
                    return False
                
                current_status = result[0]
                new_status = not current_status
                
                if new_status:
                    # Mark as completed
                    cursor.execute("""
                        UPDATE checklist_items 
                        SET completed = ?, completed_by = ?, completed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_status, user_id, item_id))
                else:
                    # Mark as not completed
                    cursor.execute("""
                        UPDATE checklist_items 
                        SET completed = ?, completed_by = NULL, completed_at = NULL
                        WHERE id = ?
                    """, (new_status, item_id))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error toggling checklist item: {e}")
            return False
    
    def get_upcoming_appointments_for_reminders(self, minutes_ahead: int = 60) -> List[Dict[str, Any]]:
        """Get appointments that need reminders sent."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.*, 
                           u1.telegram_id as creator_telegram_id,
                           u2.telegram_id as shared_telegram_id
                    FROM appointments a
                    JOIN users u1 ON a.created_by = u1.id
                    LEFT JOIN users u2 ON a.shared_with = u2.id
                    WHERE a.reminder_sent = FALSE
                    AND a.appointment_date BETWEEN 
                        datetime('now') 
                        AND datetime('now', '+{} minutes')
                """.format(minutes_ahead))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Error getting appointments for reminders: {e}")
            return []
    
    def mark_reminder_sent(self, appointment_id: int) -> bool:
        """Mark an appointment reminder as sent."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE appointments SET reminder_sent = TRUE WHERE id = ?
                """, (appointment_id,))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error marking reminder as sent: {e}")
            return False