import asyncio
import logging
import schedule
import time
from threading import Thread
from typing import List, Dict, Any
from datetime import datetime, timedelta
from database import DatabaseManager
from telegram import Bot
from telegram.constants import ParseMode


class ReminderService:
    """Handles appointment reminders and notifications."""
    
    def __init__(self, db: DatabaseManager, bot: Bot):
        self.db = db
        self.bot = bot
        self.running = False
        self.reminder_thread = None
        
        # Schedule reminder checks
        schedule.every(5).minutes.do(self._check_and_send_reminders)
        
        logging.info("Reminder service initialized")
    
    def start(self):
        """Start the reminder service."""
        if not self.running:
            self.running = True
            self.reminder_thread = Thread(target=self._run_scheduler, daemon=True)
            self.reminder_thread.start()
            logging.info("Reminder service started")
    
    def stop(self):
        """Stop the reminder service."""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread.join()
        logging.info("Reminder service stopped")
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread."""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def _check_and_send_reminders(self):
        """Check for appointments that need reminders and send them."""
        try:
            # Get appointments that need reminders (60 minutes ahead)
            appointments = self.db.get_upcoming_appointments_for_reminders(60)
            
            for appointment in appointments:
                asyncio.create_task(self._send_reminder(appointment))
                
        except Exception as e:
            logging.error(f"Error checking reminders: {e}")
    
    async def _send_reminder(self, appointment: Dict[str, Any]):
        """Send a reminder for a specific appointment."""
        try:
            appointment_time = datetime.fromisoformat(appointment['appointment_date'])
            time_until = appointment_time - datetime.now()
            
            # Create reminder message
            message = self._format_reminder_message(appointment, time_until)
            
            # Send to creator
            if appointment.get('creator_telegram_id'):
                try:
                    await self.bot.send_message(
                        chat_id=appointment['creator_telegram_id'],
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logging.info(f"Reminder sent to creator {appointment['creator_telegram_id']} for appointment {appointment['id']}")
                except Exception as e:
                    logging.error(f"Failed to send reminder to creator: {e}")
            
            # Send to shared user
            if appointment.get('shared_telegram_id') and appointment['shared_telegram_id'] != appointment.get('creator_telegram_id'):
                try:
                    await self.bot.send_message(
                        chat_id=appointment['shared_telegram_id'],
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logging.info(f"Reminder sent to shared user {appointment['shared_telegram_id']} for appointment {appointment['id']}")
                except Exception as e:
                    logging.error(f"Failed to send reminder to shared user: {e}")
            
            # Mark reminder as sent
            self.db.mark_reminder_sent(appointment['id'])
            
        except Exception as e:
            logging.error(f"Error sending reminder for appointment {appointment.get('id')}: {e}")
    
    def _format_reminder_message(self, appointment: Dict[str, Any], time_until: timedelta) -> str:
        """Format the reminder message."""
        title = appointment.get('title', 'Appointment')
        location = appointment.get('location', '')
        description = appointment.get('description', '')
        appointment_date = appointment.get('appointment_date', '')
        
        # Format time until appointment
        total_minutes = int(time_until.total_seconds() / 60)
        if total_minutes < 60:
            time_str = f"{total_minutes} minutes"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            time_str = f"{hours} hour{'s' if hours != 1 else ''}"
            if minutes > 0:
                time_str += f" and {minutes} minute{'s' if minutes != 1 else ''}"
        
        message = f"🔔 **Appointment Reminder**\n\n"
        message += f"📅 **{title}**\n"
        message += f"🕐 Starting in {time_str}\n"
        
        # Parse and format the appointment date
        try:
            dt = datetime.fromisoformat(appointment_date.replace(' ', 'T'))
            formatted_date = dt.strftime('%A, %B %d at %I:%M %p')
            message += f"📆 {formatted_date}\n"
        except:
            message += f"📆 {appointment_date}\n"
        
        if location:
            message += f"📍 {location}\n"
        
        if description:
            message += f"📝 {description}\n"
        
        message += "\n💡 Don't forget to prepare and leave on time!"
        
        return message
    
    async def send_custom_reminder(self, user_telegram_id: int, message: str, delay_minutes: int = 0):
        """Send a custom reminder to a user."""
        try:
            if delay_minutes > 0:
                # Schedule for later
                await asyncio.sleep(delay_minutes * 60)
            
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=f"🔔 **Reminder**\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            logging.info(f"Custom reminder sent to user {user_telegram_id}")
            
        except Exception as e:
            logging.error(f"Error sending custom reminder: {e}")
    
    async def send_appointment_update_notification(self, appointment: Dict[str, Any], 
                                                  update_type: str, user_telegram_id: int):
        """Send notification when an appointment is updated."""
        try:
            title = appointment.get('title', 'Appointment')
            
            if update_type == 'created':
                message = f"✅ **New Appointment Created**\n\n📅 **{title}**\n"
            elif update_type == 'updated':
                message = f"📝 **Appointment Updated**\n\n📅 **{title}**\n"
            elif update_type == 'deleted':
                message = f"🗑 **Appointment Deleted**\n\n📅 **{title}**\n"
            else:
                message = f"📅 **Appointment {update_type}**\n\n**{title}**\n"
            
            # Add appointment details for created/updated
            if update_type in ['created', 'updated']:
                if appointment.get('appointment_date'):
                    try:
                        dt = datetime.fromisoformat(appointment['appointment_date'].replace(' ', 'T'))
                        formatted_date = dt.strftime('%A, %B %d at %I:%M %p')
                        message += f"📆 {formatted_date}\n"
                    except:
                        message += f"📆 {appointment['appointment_date']}\n"
                
                if appointment.get('location'):
                    message += f"📍 {appointment['location']}\n"
                
                if appointment.get('description'):
                    message += f"📝 {appointment['description']}\n"
            
            # Send to paired user
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if user:
                paired_user = self.db.get_paired_user(user_telegram_id)
                if paired_user:
                    await self.bot.send_message(
                        chat_id=paired_user['telegram_id'],
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logging.info(f"Appointment notification sent to paired user {paired_user['telegram_id']}")
            
        except Exception as e:
            logging.error(f"Error sending appointment update notification: {e}")
    
    async def send_checklist_notification(self, checklist: Dict[str, Any], 
                                        notification_type: str, user_telegram_id: int):
        """Send notification for checklist updates."""
        try:
            title = checklist.get('title', 'Checklist')
            
            if notification_type == 'created':
                message = f"✅ **New Checklist Created**\n\n📋 **{title}**\n"
            elif notification_type == 'item_completed':
                message = f"✅ **Checklist Item Completed**\n\n📋 **{title}**\n"
            elif notification_type == 'completed':
                message = f"🎉 **Checklist Completed**\n\n📋 **{title}**\n"
            else:
                message = f"📋 **Checklist {notification_type}**\n\n**{title}**\n"
            
            if checklist.get('description'):
                message += f"📝 {checklist['description']}\n"
            
            # Send to paired user
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if user:
                paired_user = self.db.get_paired_user(user_telegram_id)
                if paired_user:
                    await self.bot.send_message(
                        chat_id=paired_user['telegram_id'],
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logging.info(f"Checklist notification sent to paired user {paired_user['telegram_id']}")
            
        except Exception as e:
            logging.error(f"Error sending checklist notification: {e}")
    
    async def send_daily_summary(self, user_telegram_id: int):
        """Send daily summary of appointments and checklist progress."""
        try:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            # Get today's appointments
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return
            
            user_id = user['id']
            
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get today's appointments
                cursor.execute("""
                    SELECT * FROM appointments
                    WHERE (created_by = ? OR shared_with = ?)
                    AND appointment_date >= ? AND appointment_date < ?
                    ORDER BY appointment_date ASC
                """, (user_id, user_id, today.isoformat(), tomorrow.isoformat()))
                
                appointments = [dict(row) for row in cursor.fetchall()]
            
            # Get incomplete checklist items
            incomplete_items = []
            checklists = self.db.get_checklists(user_telegram_id)
            for checklist in checklists:
                items = self.db.get_checklist_items(checklist['id'])
                incomplete = [item for item in items if not item['completed']]
                if incomplete:
                    incomplete_items.append({
                        'checklist': checklist['title'],
                        'items': len(incomplete)
                    })
            
            # Format summary message
            message = f"🌅 **Daily Summary for {today.strftime('%A, %B %d')}**\n\n"
            
            if appointments:
                message += "📅 **Today's Appointments:**\n"
                for apt in appointments:
                    try:
                        dt = datetime.fromisoformat(apt['appointment_date'])
                        time_str = dt.strftime('%I:%M %p')
                        message += f"• {apt['title']} at {time_str}\n"
                    except:
                        message += f"• {apt['title']}\n"
                message += "\n"
            else:
                message += "📅 No appointments scheduled for today\n\n"
            
            if incomplete_items:
                message += "✅ **Pending Checklist Items:**\n"
                for item in incomplete_items:
                    message += f"• {item['checklist']}: {item['items']} item{'s' if item['items'] != 1 else ''}\n"
                message += "\n"
            else:
                message += "✅ All checklist items completed!\n\n"
            
            message += "Have a great day! 🌟"
            
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logging.info(f"Daily summary sent to user {user_telegram_id}")
            
        except Exception as e:
            logging.error(f"Error sending daily summary: {e}")
    
    def schedule_custom_reminder(self, user_telegram_id: int, message: str, 
                               reminder_time: datetime):
        """Schedule a custom reminder for a specific time."""
        try:
            delay_seconds = (reminder_time - datetime.now()).total_seconds()
            if delay_seconds > 0:
                asyncio.create_task(
                    self._delayed_reminder(user_telegram_id, message, delay_seconds)
                )
                logging.info(f"Custom reminder scheduled for user {user_telegram_id}")
                return True
            else:
                logging.warning("Cannot schedule reminder in the past")
                return False
                
        except Exception as e:
            logging.error(f"Error scheduling custom reminder: {e}")
            return False
    
    async def _delayed_reminder(self, user_telegram_id: int, message: str, delay_seconds: float):
        """Send a delayed reminder."""
        try:
            await asyncio.sleep(delay_seconds)
            await self.send_custom_reminder(user_telegram_id, message)
        except Exception as e:
            logging.error(f"Error sending delayed reminder: {e}")