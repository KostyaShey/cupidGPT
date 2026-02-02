import os
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
from telegram import (
    Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, filters, CallbackQueryHandler
)
from telegram.constants import ParseMode

from database import DatabaseManager
from llm_client import LLMClient
from user_manager import UserManager
from appointment_manager import AppointmentManager
from checklist_manager import ChecklistManager
from reminder_service import ReminderService


class CupidGPTBot:
    """Main bot class that coordinates all functionality."""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize logging
        self.setup_logging()
        
        # Initialize components
        self.db = DatabaseManager(os.getenv('DATABASE_PATH', 'data/cupidgpt.db'))
        self.openai_client = LLMClient(os.getenv('GEMINI_API_KEY'))
        self.user_manager = UserManager(self.db)
        self.appointment_manager = AppointmentManager(self.db, self.openai_client)
        self.checklist_manager = ChecklistManager(self.db, self.openai_client)
        
        # Debug mode
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        # Initialize Telegram bot
        self.app = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
        self.setup_handlers()
        
        # Initialize reminder service
        self.reminder_service = ReminderService(self.db, self.app.bot)
        
        logging.info("CupidGPT Bot initialized successfully")
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
        log_file = os.getenv('LOG_FILE', 'logs/cupidgpt.log')
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def setup_handlers(self):
        """Setup command and message handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("pair", self.pair_command))
        self.app.add_handler(CommandHandler("new_appointment", self.new_appointment_command))
        self.app.add_handler(CommandHandler("list_appointments", self.list_appointments_command))
        self.app.add_handler(CommandHandler("new_checklist", self.new_checklist_command))
        self.app.add_handler(CommandHandler("view_checklist", self.view_checklist_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        
        # Message handler for natural language processing
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Callback query handler for inline keyboards
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
    
    def get_main_menu_keyboard(self):
        """Returns the main menu inline keyboard."""
        keyboard = [
            [InlineKeyboardButton("📅 Appointments", callback_data="menu:appointments")],
            [InlineKeyboardButton("✅ Checklists", callback_data="menu:checklists")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_appointments_menu_keyboard(self):
        """Returns the appointments submenu inline keyboard."""
        keyboard = [
            [InlineKeyboardButton("➕ Create new appointment", callback_data="action:new_appointment")],
            [InlineKeyboardButton("📋 Show upcoming appointments", callback_data="action:list_appointments")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu:main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_checklists_menu_keyboard(self):
        """Returns the checklists submenu inline keyboard."""
        keyboard = [
            [InlineKeyboardButton("➕ Create new checklist", callback_data="action:new_checklist")],
            [InlineKeyboardButton("📋 Show existing Checklists", callback_data="action:view_checklist")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu:main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_settings_menu_keyboard(self):
        """Returns the settings submenu inline keyboard."""
        keyboard = [
            [InlineKeyboardButton("🔗 Pair with a user", callback_data="action:pair")],
            [InlineKeyboardButton("📊 Account status", callback_data="action:status")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu:main")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_persistent_menu_keyboard(self):
        """Returns the persistent reply keyboard for main navigation."""
        keyboard = [
            [KeyboardButton("📅 Appointments"), KeyboardButton("✅ Checklists")],
            [KeyboardButton("🏠 Home")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Register user
        success = self.user_manager.register_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        if success:
            welcome_message = f"""
🎯 *Welcome to CupidGPT!* 🎯

Hello {user.first_name}! I'm your personal appointment and checklist assistant.

*What I can do:*
• 📅 Help you create and manage appointments
• ✅ Create and share checklists with your partner
• 🔔 Send reminders for upcoming appointments
• 🤖 Understand natural language for easy interaction

*Getting Started:*
1. First, you need to pair with your partner using `/pair @username`
2. Then you can start creating appointments and checklists!

Use `/help` to see all available commands.
            """
            
            # Create keyboard
            reply_markup = self.get_persistent_menu_keyboard()

            await update.effective_message.reply_text(
                welcome_message, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await update.effective_message.reply_text(
                "❌ Sorry, there was an error registering your account. Please try again."
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🤖 *CupidGPT Commands*

*User Management:*
• `/start` - Initialize bot and register
• `/pair @username` - Pair with your partner
• `/status` - Check your pairing status

*Appointments:*
• `/new_appointment` - Create a new appointment
• `/list_appointments` - View upcoming appointments

*Checklists:*
• `/new_checklist` - Create a new checklist
• `/view_checklist` - View existing checklists

*Smart Features:*
Just send me a message in natural language like:
• "Remind me about dinner on Friday at 7pm"
• "Create a grocery list with milk, bread, and eggs"
• "We have a meeting tomorrow at the office"

I'll automatically parse your request and create appointments or checklist items!

*Need Help?*
Type `/help` anytime to see this message again.
        """
        
        await update.effective_message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def pair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pair command."""
        if not context.args:
            await update.effective_message.reply_text(
                "Please provide your partner's username: `/pair @username`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        partner_username = context.args[0].replace('@', '')
        result = await self.user_manager.pair_users(update.effective_user.id, partner_username)
        
        if result['success']:
            await update.effective_message.reply_text(
                f"✅ {result['message']}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.effective_message.reply_text(
                f"❌ {result['message']}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        status = self.user_manager.get_user_status(update.effective_user.id)
        await update.effective_message.reply_text(status, parse_mode=ParseMode.MARKDOWN)
    
    async def new_appointment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new_appointment command."""
        if not self.debug_mode and not self.user_manager.is_user_paired(update.effective_user.id):
            await update.effective_message.reply_text(
                "❌ You need to pair with your partner first. Use `/pair @username`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.effective_message.reply_text(
            "📅 *Creating New Appointment*\n\n"
            "Please describe your appointment. You can include:\n"
            "• Date and time\n"
            "• Location\n"
            "• Description\n\n"
            "Example: 'Dinner at Mario's restaurant tomorrow at 7pm'",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Set state for next message
        context.user_data['waiting_for'] = 'appointment'
    
    async def list_appointments_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_appointments command."""
        appointments = await self.appointment_manager.get_user_appointments(update.effective_user.id)
        
        if not appointments:
            await update.effective_message.reply_text(
                "📅 No upcoming appointments found.",
                reply_markup=self.get_appointments_menu_keyboard()
            )
            return
        
        message = "📅 *Upcoming Appointments:*\n\n"
        for apt in appointments:
            message += f"• *{apt['title']}*\n"
            message += f"  📍 {apt.get('location', 'No location')}\n"
            message += f"  🕐 {apt['appointment_date']}\n"
            if apt.get('description'):
                message += f"  📝 {apt['description']}\n"
            message += f"  👤 Created by: {apt.get('creator_name', 'Unknown')}\n\n"
        
        await update.effective_message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_appointments_menu_keyboard()
        )
    
    async def new_checklist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new_checklist command."""
        if not self.debug_mode and not self.user_manager.is_user_paired(update.effective_user.id):
            await update.effective_message.reply_text(
                "❌ You need to pair with your partner first. Use `/pair @username`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.effective_message.reply_text(
            "✅ *Creating New Checklist*\n\n"
            "Please provide:\n"
            "1. Checklist title\n"
            "2. Items (one per line or comma-separated)\n\n"
            "Example: 'Grocery Shopping\\nMilk\\nBread\\nEggs\\nApples'",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Set state for next message
        context.user_data['waiting_for'] = 'checklist'
    
    async def view_checklist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_checklist command."""
        checklists = await self.checklist_manager.get_user_checklists(update.effective_user.id)
        
        if not checklists:
            await update.effective_message.reply_text(
                "✅ No checklists found.",
                reply_markup=self.get_checklists_menu_keyboard()
            )
            return
        
        # For now, just show the first checklist
        # In a full implementation, you'd show a selection menu
        checklist = checklists[0]
        items = await self.checklist_manager.get_checklist_items(checklist['id'])
        
        message = f"✅ *{checklist['title']}*\n\n"
        if checklist.get('description'):
            message += f"📝 {checklist['description']}\n\n"
        
        for item in items:
            status = "✅" if item['completed'] else "⬜"
            message += f"{status} {item['text']}\n"
            if item['completed'] and item.get('completed_by_name'):
                message += f"   └ Completed by {item['completed_by_name']}\n"
        
        await update.effective_message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_checklists_menu_keyboard()
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with navigation and natural language processing."""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # --- Navigation & Menus (Legacy Support/Text Fallback) ---
        
        if await self._handle_menu_navigation(message_text, update):
            return

        if await self._handle_menu_actions(message_text, update, context):
            return

        if await self._handle_legacy_commands(message_text, update, context):
            return

        # --- Logic Checks ---
        
        # Check if user is paired (required for most actions)
        if not self.user_manager.is_user_paired(user_id):
            # Allow Pairing/Settings interactions even if not paired? 
            # If they are just navigating menus, we shouldn't block. 
            pass 
        
        # Check if we're waiting for specific input
        waiting_for = context.user_data.get('waiting_for')
        if waiting_for:
            await self._process_pending_input(message_text, waiting_for, update, context)
            return

        # General natural language processing
        result = await self.process_natural_language(message_text, user_id)
        await update.effective_message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _handle_menu_navigation(self, text: str, update: Update) -> bool:
        """Handle main menu navigation commands."""
        if text in ["Agendas", "📅 Appointments", "Appointments", "/appointments"]:
            await update.effective_message.reply_text("📅 *Appointments Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=self.get_appointments_menu_keyboard())
            return True
        elif text in ["✅ Checklists", "Checklists", "/checklists"]:
            await update.effective_message.reply_text("✅ *Checklists Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=self.get_checklists_menu_keyboard())
            return True
        elif text in ["Settings", "/settings"]:
            await update.effective_message.reply_text("⚙️ *Settings Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=self.get_settings_menu_keyboard())
            return True
        elif text in ["🏠 Home", "Home", "Back"]:
            await update.effective_message.reply_text("🏠 *Home*", parse_mode=ParseMode.MARKDOWN, reply_markup=self.get_main_menu_keyboard())
            return True
        return False

    async def _handle_menu_actions(self, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle specific menu actions."""
        if text == "Create new appointment":
            await self.new_appointment_command(update, context)
            return True
        elif text == "Show upcoming appointments":
            await self.list_appointments_command(update, context)
            return True
        elif text == "Create new checklist":
            await self.new_checklist_command(update, context)
            return True
        elif text == "Show existing Checklists":
            await self.view_checklist_command(update, context)
            return True
        elif text == "Pair with a user":
            await self.pair_command(update, context)
            return True
        elif text == "Account status":
            await self.status_command(update, context)
            return True
        return False

    async def _handle_legacy_commands(self, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle legacy or direct commands."""
        if text == "Pair": 
             await self.pair_command(update, context)
             return True
        elif text == "Status":
             await self.status_command(update, context)
             return True
        elif text == "New Appointment":
             await self.new_appointment_command(update, context)
             return True
        elif text == "List Appointments":
             await self.list_appointments_command(update, context)
             return True
        elif text == "New Checklist":
             await self.new_checklist_command(update, context)
             return True
        elif text == "View Checklists":
             await self.view_checklist_command(update, context)
             return True
        return False

    async def _process_pending_input(self, text: str, waiting_for: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process input when waiting for specific details."""
        if waiting_for == 'appointment':
             # Instead of creating immediately, extract details and ask for confirmation
            details = await self.openai_client.extract_appointment_details(text)
            context.user_data.pop('waiting_for', None)
            
            if not details.get('success'):
                await update.effective_message.reply_text(
                    f"❌ {details.get('error', 'Failed to understand appointment details')}",
                    reply_markup=self.get_appointments_menu_keyboard()
                )
                return

            # Store details in user_data for callback access
            context.user_data['pending_appointment'] = details
            
            preview_msg = (
                f"📅 *Confirm Appointment*\n\n"
                f"Title: {details['title']}\n"
                f"Date: {details['appointment_datetime']}\n"
                f"Location: {details.get('location', 'Not specified')}\n"
                f"Description: {details.get('description', 'None')}\n\n"
                f"Does this look correct?"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="confirm:appointment"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel:appointment")
                ]
            ]
            
            await update.effective_message.reply_text(
                preview_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif waiting_for == 'checklist':
             # Instead of creating immediately, extract details and ask for confirmation
            details = await self.openai_client.extract_checklist_details(text)
            context.user_data.pop('waiting_for', None)
            
            if not details.get('success'):
                await update.effective_message.reply_text(
                    f"❌ {details.get('error', 'Failed to understand checklist details')}",
                    reply_markup=self.get_checklists_menu_keyboard()
                )
                return

            # Store details in user_data for callback access
            context.user_data['pending_checklist'] = details
            
            items_str = "\\n".join([f"• {item}" for item in details['items']])
            preview_msg = (
                f"📋 *Confirm Checklist*\n\n"
                f"Title: {details['title']}\n"
                f"Description: {details.get('description', 'None')}\n\n"
                f"Items:\n{items_str}\n\n"
                f"Does this look correct?"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="confirm:checklist"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel:checklist")
                ]
            ]
            
            await update.effective_message.reply_text(
                preview_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def process_natural_language(self, text: str, user_id: int) -> str:
        """Process natural language input to determine intent."""
        try:
            # Use OpenAI to determine intent
            intent = await self.openai_client.determine_intent(text)
            
            if intent['type'] == 'appointment':
                result = await self.appointment_manager.create_appointment_from_text(text, user_id)
                if result['success']:
                    return f"✅ Created appointment: *{result['appointment']['title']}*"
                else:
                    return f"❌ {result['message']}"
            
            elif intent['type'] == 'checklist':
                result = await self.checklist_manager.create_checklist_from_text(text, user_id)
                if result['success']:
                    return f"✅ Created checklist: *{result['checklist']['title']}*"
                else:
                    return f"❌ {result['message']}"
            
            else:
                return ("🤔 I'm not sure what you want me to do. Try using one of the commands "
                       "like `/new_appointment` or `/new_checklist`, or be more specific!")
                
        except Exception as e:
            logging.error(f"Error processing natural language: {e}")
            return "❌ Sorry, I had trouble understanding that. Please try again or use a specific command."
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        user_id = update.effective_user.id
        # We'll answer the query within specific branches to allow custom toast messages
        
        # Parse callback data
        data = query.data.split(':')
        category = data[0]
        action = data[1]
        
        if category == 'menu':
            await self._handle_menu_callback(query, action)
        elif category == 'action':
            await self._handle_action_callback(query, action, update, context)
        elif category == 'confirm':
            await self._handle_confirm_callback(query, action, user_id, context)
        elif category == 'cancel':
            await self._handle_cancel_callback(query, action, context)
        elif category == 'toggle_item':
             await self._handle_toggle_item_callback(query, action, user_id)

    async def _handle_menu_callback(self, query, action):
        """Handle menu navigation callbacks."""
        await query.answer()
        if action == 'main':
            await query.edit_message_text(
                "🔙 *Main Menu*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_menu_keyboard()
            )
        elif action == 'appointments':
            await query.edit_message_text(
                "📅 *Appointments Menu*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_appointments_menu_keyboard()
            )
        elif action == 'checklists':
            await query.edit_message_text(
                "✅ *Checklists Menu*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_checklists_menu_keyboard()
            )
        elif action == 'settings':
            await query.edit_message_text(
                "⚙️ *Settings Menu*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_settings_menu_keyboard()
            )

    async def _handle_action_callback(self, query, action, update, context):
        """Handle specific action callbacks."""
        await query.answer()
        if action == 'new_appointment':
            await self.new_appointment_command(update, context)
        elif action == 'list_appointments':
            await self.list_appointments_command(update, context)
        elif action == 'new_checklist':
            await self.new_checklist_command(update, context)
        elif action == 'view_checklist':
            await self.view_checklist_command(update, context)
        elif action == 'pair':
            await self.pair_command(update, context)
        elif action == 'status':
            await self.status_command(update, context)

    async def _handle_confirm_callback(self, query, action, user_id, context):
        """Handle confirmation callbacks."""
        if action == 'appointment':
            details = context.user_data.pop('pending_appointment', None)
            if not details:
                await query.answer("❌ Error: Invitation expired.")
                return
            
            # Actually create the appointment
            appointment_datetime = datetime.fromisoformat(details['appointment_datetime'])
            appointment_id = self.db.create_appointment(
                title=details['title'],
                description=details.get('description', ''),
                appointment_date=appointment_datetime,
                location=details.get('location', ''),
                created_by_telegram_id=user_id
            )
            
            if appointment_id:
                await query.answer("✅ Appointment created successfully!", show_alert=False)
                await query.edit_message_text(
                    f"✅ *Appointment Created!*\n\n"
                    f"📅 *{details['title']}*\n"
                    f"🕐 {details['appointment_datetime']}\n"
                    f"📍 {details.get('location', 'No location')}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.get_appointments_menu_keyboard()
                )
            else:
                await query.answer("❌ Failed to save appointment.")
                await query.edit_message_text(
                    "❌ Failed to save appointment to database.",
                    reply_markup=self.get_appointments_menu_keyboard()
                )
        
        elif action == 'checklist':
            details = context.user_data.pop('pending_checklist', None)
            if not details:
                await query.answer("❌ Error: Invitation expired.")
                return
            
            # Actually create the checklist
            checklist_id = self.db.create_checklist(
                title=details['title'],
                description=details.get('description', ''),
                created_by_telegram_id=user_id
            )
            
            if checklist_id:
                items_added = []
                for item_text in details['items']:
                    if self.db.add_checklist_item(checklist_id, item_text):
                        items_added.append(item_text)
                
                await query.answer("✅ Checklist created successfully!", show_alert=False)
                await query.edit_message_text(
                    f"✅ *Checklist Created!*\n\n"
                    f"📋 *{details['title']}*\n"
                    f"Items: {len(items_added)}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.get_checklists_menu_keyboard()
                )
            else:
                await query.answer("❌ Failed to create checklist.")
                await query.edit_message_text(
                    "❌ Failed to create checklist in database.",
                    reply_markup=self.get_checklists_menu_keyboard()
                )

    async def _handle_cancel_callback(self, query, action, context):
        """Handle cancellation callbacks."""
        context.user_data.pop(f'pending_{action}', None)
        await query.answer("❌ Creation cancelled.")
        if action == 'appointment':
            await query.edit_message_text("❌ Appointment creation cancelled.", reply_markup=self.get_appointments_menu_keyboard())
        elif action == 'checklist':
            await query.edit_message_text("❌ Checklist creation cancelled.", reply_markup=self.get_checklists_menu_keyboard())

    async def _handle_toggle_item_callback(self, query, action, user_id):
        """Handle toggle item callbacks."""
        item_id = int(action)
        success = self.checklist_manager.toggle_item(item_id, user_id)
        
        if success:
            await query.answer("✅ Item status updated!")
            
            # Fetch item to get checklist ID
            item = self.db.get_checklist_item(item_id)
            if item:
                checklist_id = item['checklist_id']
                summary = await self.checklist_manager.get_checklist_summary(checklist_id)
                
                # Get toggle buttons
                items = await self.checklist_manager.get_checklist_items(checklist_id)
                keyboard = []
                for item in items:
                    status = "✅" if item['completed'] else "⬜"
                    keyboard.append([InlineKeyboardButton(
                        f"{status} {item['text']}", 
                        callback_data=f"toggle_item:{item['id']}"
                    )])
                keyboard.append([InlineKeyboardButton("🔙 Back to Checklists", callback_data="menu:checklists")])
                
                await query.edit_message_text(
                    summary,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await query.answer("❌ Failed to update item status.", show_alert=True)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logging.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again or contact support."
            )
    
    def run(self):
        """Start the bot."""
        logging.info("Starting CupidGPT Bot...")
        
        # Start reminder service
        self.reminder_service.start()
        
        # Run the bot
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = CupidGPTBot()
    bot.run()