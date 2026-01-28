import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton
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
            keyboard = [
                [KeyboardButton("Appointments"), KeyboardButton("Checklists")],
                [KeyboardButton("Settings")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                welcome_message, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
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
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def pair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pair command."""
        if not context.args:
            await update.message.reply_text(
                "Please provide your partner's username: `/pair @username`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        partner_username = context.args[0].replace('@', '')
        result = await self.user_manager.pair_users(update.effective_user.id, partner_username)
        
        if result['success']:
            await update.message.reply_text(
                f"✅ {result['message']}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"❌ {result['message']}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        status = self.user_manager.get_user_status(update.effective_user.id)
        await update.message.reply_text(status, parse_mode=ParseMode.MARKDOWN)
    
    async def new_appointment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new_appointment command."""
        if not self.debug_mode and not self.user_manager.is_user_paired(update.effective_user.id):
            await update.message.reply_text(
                "❌ You need to pair with your partner first. Use `/pair @username`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.message.reply_text(
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
        
        # Create Appointments submenu keyboard
        keyboard = [
            [KeyboardButton("Create new appointment"), KeyboardButton("Show upcoming appointments")],
            [KeyboardButton("Back")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not appointments:
            await update.message.reply_text(
                "📅 No upcoming appointments found.",
                reply_markup=reply_markup
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
        
        await update.message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def new_checklist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new_checklist command."""
        if not self.debug_mode and not self.user_manager.is_user_paired(update.effective_user.id):
            await update.message.reply_text(
                "❌ You need to pair with your partner first. Use `/pair @username`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.message.reply_text(
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
        
        # Create Checklists submenu keyboard
        keyboard = [
            [KeyboardButton("Create new checklist"), KeyboardButton("Show existing Checklists")],
            [KeyboardButton("Back")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not checklists:
            await update.message.reply_text(
                "✅ No checklists found.",
                reply_markup=reply_markup
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
        
        await update.message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with navigation and natural language processing."""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # --- Navigation & Menus ---
        
        if message_text == "Appointments":
            keyboard = [
                [KeyboardButton("Create new appointment"), KeyboardButton("Show upcoming appointments")],
                [KeyboardButton("Back")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("📅 *Appointments Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            return

        elif message_text == "Checklists":
            keyboard = [
                [KeyboardButton("Create new checklist"), KeyboardButton("Show existing Checklists")],
                [KeyboardButton("Back")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("✅ *Checklists Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            return

        elif message_text == "Settings":
            keyboard = [
                [KeyboardButton("Pair with a user"), KeyboardButton("Account status")],
                [KeyboardButton("Back")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("⚙️ *Settings Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            return

        elif message_text == "Back":
            # Return to Main Menu
            keyboard = [
                [KeyboardButton("Appointments"), KeyboardButton("Checklists")],
                [KeyboardButton("Settings")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("🔙 *Main Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            return

        # --- Specific Actions (Leaf Nodes) ---

        # Appointments Actions
        elif message_text == "Create new appointment":
            await self.new_appointment_command(update, context)
            return
        elif message_text == "Show upcoming appointments":
            await self.list_appointments_command(update, context)
            return

        # Checklists Actions
        elif message_text == "Create new checklist":
            await self.new_checklist_command(update, context)
            return
        elif message_text == "Show existing Checklists":
            await self.view_checklist_command(update, context)
            return
            
        # Settings Actions
        elif message_text == "Pair with a user":
            await self.pair_command(update, context)
            return
        elif message_text == "Account status":
            await self.status_command(update, context)
            return
            
        # --- Legacy / Direct Commands (keep these if user manually types them or from old keyboard, though user requested specific structure) ---
        elif message_text == "Pair": # Legacy support or if user types it
             await self.pair_command(update, context)
             return
        elif message_text == "Status":
             await self.status_command(update, context)
             return
        elif message_text == "New Appointment":
             await self.new_appointment_command(update, context)
             return
        elif message_text == "List Appointments":
             await self.list_appointments_command(update, context)
             return
        elif message_text == "New Checklist":
             await self.new_checklist_command(update, context)
             return
        elif message_text == "View Checklists":
             await self.view_checklist_command(update, context)
             return

        # --- Logic Checks ---
        
        # Check if user is paired (required for most actions)
        if not self.user_manager.is_user_paired(user_id):
            # Allow Pairing/Settings interactions even if not paired? 
            # If they are just navigating menus, we shouldn't block. 
            # But deep actions (creating appointments) are already protected in their respective command handlers.
            pass 
        
        # Check if we're waiting for specific input
        waiting_for = context.user_data.get('waiting_for')
        
        if waiting_for == 'appointment':
            result = await self.appointment_manager.create_appointment_from_text(
                message_text, user_id
            )
            context.user_data.pop('waiting_for', None)
            
            # Create Appointments submenu keyboard
            keyboard = [
                [KeyboardButton("Create new appointment"), KeyboardButton("Show upcoming appointments")],
                [KeyboardButton("Back")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ Appointment created successfully!\n\n"
                    f"📅 *{result['appointment']['title']}*\n"
                    f"🕐 {result['appointment']['appointment_date']}\n"
                    f"📍 {result['appointment'].get('location', 'No location')}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"❌ {result['message']}",
                    reply_markup=reply_markup
                )
        
        elif waiting_for == 'checklist':
            result = await self.checklist_manager.create_checklist_from_text(
                message_text, user_id
            )
            context.user_data.pop('waiting_for', None)
            
            # Create Checklists submenu keyboard
            keyboard = [
                [KeyboardButton("Create new checklist"), KeyboardButton("Show existing Checklists")],
                [KeyboardButton("Back")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ Checklist created successfully!\n\n"
                    f"📋 *{result['checklist']['title']}*\n"
                    f"Items: {len(result['items'])}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"❌ {result['message']}",
                    reply_markup=reply_markup
                )
        
        else:
            # General natural language processing
            # Only do NLP if it's not one of the menu commands
            result = await self.process_natural_language(message_text, user_id)
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
    
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
        await query.answer()
        
        # Parse callback data
        data = query.data.split(':')
        action = data[0]
        
        if action == 'toggle_item':
            item_id = int(data[1])
            result = self.checklist_manager.toggle_item(item_id, update.effective_user.id)
            
            if result:
                await query.edit_message_text("✅ Item status updated!")
            else:
                await query.edit_message_text("❌ Failed to update item status.")
    
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