import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database import DatabaseManager
from llm_client import LLMClient


class AppointmentManager:
    """Manages appointment creation, retrieval, and operations."""
    
    def __init__(self, db: DatabaseManager, openai_client: LLMClient):
        self.db = db
        self.openai_client = openai_client
    
    async def create_appointment_from_text(self, text: str, user_telegram_id: int) -> Dict[str, Any]:
        """Create an appointment from natural language text."""
        try:
            # Extract appointment details using OpenAI
            details = await self.openai_client.extract_appointment_details(text)
            
            if not details.get('success'):
                return {
                    'success': False,
                    'message': details.get('error', 'Failed to understand appointment details')
                }
            
            # Parse the datetime
            appointment_datetime = datetime.fromisoformat(details['appointment_datetime'])
            
            # Validate appointment time (not in the past)
            if appointment_datetime < datetime.now():
                return {
                    'success': False,
                    'message': "Cannot create appointments in the past"
                }
            
            # Create the appointment
            appointment_id = self.db.create_appointment(
                title=details['title'],
                description=details.get('description', ''),
                appointment_date=appointment_datetime,
                location=details.get('location', ''),
                created_by_telegram_id=user_telegram_id
            )
            
            if appointment_id:
                appointment_data = {
                    'id': appointment_id,
                    'title': details['title'],
                    'description': details.get('description', ''),
                    'appointment_date': appointment_datetime.strftime('%Y-%m-%d %H:%M'),
                    'location': details.get('location', ''),
                    'duration_minutes': details.get('duration_minutes', 60)
                }
                
                logging.info(f"Appointment created: {appointment_id} by user {user_telegram_id}")
                
                return {
                    'success': True,
                    'appointment': appointment_data,
                    'message': 'Appointment created successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to save appointment to database'
                }
                
        except Exception as e:
            logging.error(f"Error creating appointment from text: {e}")
            return {
                'success': False,
                'message': 'An error occurred while creating the appointment'
            }
    
    async def create_appointment_manual(self, title: str, description: str, 
                                      appointment_date: datetime, location: str,
                                      user_telegram_id: int) -> Dict[str, Any]:
        """Create an appointment with manual input."""
        try:
            # Validate appointment time
            if appointment_date < datetime.now():
                return {
                    'success': False,
                    'message': "Cannot create appointments in the past"
                }
            
            appointment_id = self.db.create_appointment(
                title=title,
                description=description,
                appointment_date=appointment_date,
                location=location,
                created_by_telegram_id=user_telegram_id
            )
            
            if appointment_id:
                appointment_data = {
                    'id': appointment_id,
                    'title': title,
                    'description': description,
                    'appointment_date': appointment_date.strftime('%Y-%m-%d %H:%M'),
                    'location': location
                }
                
                logging.info(f"Manual appointment created: {appointment_id} by user {user_telegram_id}")
                
                return {
                    'success': True,
                    'appointment': appointment_data,
                    'message': 'Appointment created successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to save appointment to database'
                }
                
        except Exception as e:
            logging.error(f"Error creating manual appointment: {e}")
            return {
                'success': False,
                'message': 'An error occurred while creating the appointment'
            }
    
    async def get_user_appointments(self, user_telegram_id: int, 
                                  upcoming_only: bool = True) -> List[Dict[str, Any]]:
        """Get appointments for a user."""
        try:
            appointments = self.db.get_appointments(user_telegram_id, upcoming_only)
            
            # Format appointment dates for display
            for appointment in appointments:
                if appointment.get('appointment_date'):
                    # Parse the datetime string from database
                    dt = datetime.fromisoformat(appointment['appointment_date'].replace(' ', 'T'))
                    appointment['formatted_date'] = dt.strftime('%A, %B %d, %Y at %I:%M %p')
                    appointment['relative_time'] = self._get_relative_time(dt)
            
            return appointments
            
        except Exception as e:
            logging.error(f"Error getting user appointments: {e}")
            return []
    
    def _get_relative_time(self, appointment_date: datetime) -> str:
        """Get relative time description for an appointment."""
        now = datetime.now()
        diff = appointment_date - now
        
        if diff.days == 0:
            if diff.seconds < 3600:  # Less than 1 hour
                minutes = diff.seconds // 60
                return f"In {minutes} minutes"
            else:
                hours = diff.seconds // 3600
                return f"In {hours} hours"
        elif diff.days == 1:
            return "Tomorrow"
        elif diff.days < 7:
            return f"In {diff.days} days"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"In {weeks} weeks"
        else:
            months = diff.days // 30
            return f"In {months} months"
    
    async def get_appointment_by_id(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific appointment by ID."""
        try:
            return self.db.get_appointment_by_id(appointment_id)
        except Exception as e:
            logging.error(f"Error getting appointment by ID: {e}")
            return None
    
    async def update_appointment(self, appointment_id: int, user_telegram_id: int,
                               **updates) -> Dict[str, Any]:
        """Update an appointment."""
        try:
            # Check if user has permission to update this appointment
            appointment = await self.get_appointment_by_id(appointment_id)
            if not appointment:
                return {
                    'success': False,
                    'message': 'Appointment not found'
                }
            
            # Check if user is creator or shared user
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            user_id = user['id']
            if appointment['created_by'] != user_id and appointment.get('shared_with') != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to update this appointment'
                }
            
            # Build update query
            update_fields = []
            update_values = []
            
            for field, value in updates.items():
                if field in ['title', 'description', 'appointment_date', 'location']:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return {
                    'success': False,
                    'message': 'No valid fields to update'
                }
            
            update_values.append(appointment_id)
            
            if not self.db.update_appointment(appointment_id, updates):
                return {
                    'success': False,
                    'message': 'Failed to update appointment'
                }
            
            logging.info(f"Appointment {appointment_id} updated by user {user_telegram_id}")
            
            return {
                'success': True,
                'message': 'Appointment updated successfully'
            }
            
        except Exception as e:
            logging.error(f"Error updating appointment: {e}")
            return {
                'success': False,
                'message': 'An error occurred while updating the appointment'
            }
    
    async def delete_appointment(self, appointment_id: int, user_telegram_id: int) -> Dict[str, Any]:
        """Delete an appointment."""
        try:
            # Check if user has permission to delete this appointment
            appointment = await self.get_appointment_by_id(appointment_id)
            if not appointment:
                return {
                    'success': False,
                    'message': 'Appointment not found'
                }
            
            # Check if user is creator
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            if appointment['created_by'] != user['id']:
                return {
                    'success': False,
                    'message': 'Only the creator can delete an appointment'
                }
            
            if not self.db.delete_appointment(appointment_id):
                return {
                    'success': False,
                    'message': 'Failed to delete appointment'
                }
            
            logging.info(f"Appointment {appointment_id} deleted by user {user_telegram_id}")
            
            return {
                'success': True,
                'message': 'Appointment deleted successfully'
            }
            
        except Exception as e:
            logging.error(f"Error deleting appointment: {e}")
            return {
                'success': False,
                'message': 'An error occurred while deleting the appointment'
            }
    
    async def get_appointments_for_date(self, user_telegram_id: int, 
                                      target_date: datetime) -> List[Dict[str, Any]]:
        """Get appointments for a specific date."""
        try:
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return []
            
            user_id = user['id']
            
            return self.db.get_appointments_in_range(user_id, start_date, end_date)
                
        except Exception as e:
            logging.error(f"Error getting appointments for date: {e}")
            return []
    
    async def get_conflicting_appointments(self, user_telegram_id: int,
                                         appointment_date: datetime,
                                         duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Check for conflicting appointments."""
        try:
            start_time = appointment_date
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return []
            
            user_id = user['id']
            
            # Get appointments in the range
            appointments = self.db.get_appointments_in_range(user_id, start_time, end_time)
            
            # Since get_appointments_in_range is simple, we might need to filter manually if the conflict logic is complex
            # But for now, let's assume any overlap is a conflict. 
            # The original query checked for overlap. The helper gets appointments STARTING in range.
            # We need to refine this slightly or update the helper. The original query logic was:
            # (start_date <= start_time AND end_date > start_time) OR (start_date < end_time AND start_date >= start_time)
            
            # Actually, to avoid changing behavior too much let's keep it simple.
            # If the helper returns appointments where date >= start and date < end, that covers "starts during the new appointment"
            # It misses "started before new appointment and ends during/after".
            
            # Let's adjust the simple helper usage for now. 
            # Ideally, get_appointments_in_range should probably take an overlap check, but strictly speaking "in range" usually means "starts in range".
            
            # For this specific case, let's check for "conflicting" appointments properly by fetching appointments around the time.
            # A broad fetch then filter in python might be safer if we want to rely on the simple helper.
            # Let's fetch appointments for the day, then filter.
            
            day_start = appointment_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_appointments = self.db.get_appointments_in_range(user_id, day_start, day_end)
            
            conflicts = []
            for apt in day_appointments:
                apt_start = datetime.fromisoformat(apt['appointment_date'])
                # Assuming 1 hour duration for existing appointments if not stored
                # The schema doesn't seem to store duration?
                # Ah, the original query assumed 60 minutes for existing appointments: datetime(a.appointment_date, '+60 minutes')
                
                apt_end = apt_start + timedelta(minutes=60)
                
                # Check overlap
                if (apt_start < end_time and apt_end > start_time):
                    conflicts.append(apt)
            
            return conflicts
                
        except Exception as e:
            logging.error(f"Error checking conflicting appointments: {e}")
            return []
    
    async def export_appointments(self, user_telegram_id: int, 
                                format_type: str = 'text') -> str:
        """Export user's appointments in various formats."""
        try:
            appointments = await self.get_user_appointments(user_telegram_id, upcoming_only=False)
            
            if format_type == 'text':
                export_text = "📅 **Your Appointments**\n\n"
                
                for apt in appointments:
                    export_text += f"**{apt['title']}**\n"
                    export_text += f"Date: {apt.get('formatted_date', apt['appointment_date'])}\n"
                    if apt.get('location'):
                        export_text += f"Location: {apt['location']}\n"
                    if apt.get('description'):
                        export_text += f"Description: {apt['description']}\n"
                    export_text += "\n---\n\n"
                
                return export_text
            
            # Add more export formats as needed (CSV, JSON, etc.)
            return "Export format not supported"
            
        except Exception as e:
            logging.error(f"Error exporting appointments: {e}")
            return "Error exporting appointments"