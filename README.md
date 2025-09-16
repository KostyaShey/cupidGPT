# CupidGPT - Couple's Appointment & Checklist Bot

A sophisticated Telegram bot designed to help couples manage appointments and shared checklists using natural language processing powered by OpenAI's ChatGPT.

## 🌟 Features

### Core Functionality
- **Natural Language Processing**: Create appointments and checklists using plain English
- **Couple Pairing System**: Connect two users to share appointments and checklists
- **Smart Appointment Management**: Automatic date/time parsing and validation
- **Shared Checklist Management**: Create, track, and complete items together
- **Intelligent Reminders**: Automatic notifications before appointments
- **Link Processing**: Extract information from shared links
- **Export Functionality**: Export appointments and checklists in various formats

### Smart Features
- **Context-Aware Parsing**: Understands natural language like "dinner tomorrow at 7pm"
- **Conflict Detection**: Warns about scheduling conflicts
- **Completion Tracking**: Track checklist progress with statistics
- **Daily Summaries**: Get morning briefings of the day's schedule
- **Cross-User Notifications**: Partners get notified of new appointments/checklists

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key
- Virtual environment support

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cupidGPT
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   OPENAI_API_KEY=your_openai_api_key_here
   DATABASE_PATH=data/cupidgpt.db
   LOG_LEVEL=INFO
   LOG_FILE=logs/cupidgpt.log
   MAX_USERS=2
   REMINDER_CHECK_INTERVAL=300
   ```

5. **Run the bot**
   ```bash
   python src/bot.py
   ```

## 🛠 Configuration

### Getting API Keys

#### Telegram Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Choose a name and username for your bot
4. Copy the provided token to your `.env` file

#### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Required |
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `DATABASE_PATH` | SQLite database file path | `data/cupidgpt.db` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `LOG_FILE` | Log file path | `logs/cupidgpt.log` |
| `MAX_USERS` | Maximum users per pair | `2` |
| `REMINDER_CHECK_INTERVAL` | Reminder check interval in seconds | `300` |

## 📱 Bot Commands

### Essential Commands
- `/start` - Initialize bot and register your account
- `/help` - Display available commands and usage instructions
- `/pair @username` - Connect with your partner
- `/status` - Check your current pairing status

### Appointment Management
- `/new_appointment` - Create a new appointment
- `/list_appointments` - View your upcoming appointments

### Checklist Management
- `/new_checklist` - Create a new shared checklist
- `/view_checklist` - View existing checklists and their progress

## 🗣 Natural Language Usage

The bot understands natural language for creating appointments and checklists:

### Appointment Examples
```
"Dinner at Mario's restaurant tomorrow at 7pm"
"Meeting with John on Friday at 2:30pm at the office"
"Doctor appointment next Monday at 10am"
"Movie night tonight at 8pm"
```

### Checklist Examples
```
"Grocery Shopping
Milk
Bread
Eggs
Apples"

"Weekend Tasks: Clean house, do laundry, buy groceries"
"Travel checklist: passport, tickets, hotel confirmation"
```

## 🏗 Project Structure

```
cupidGPT/
├── src/
│   ├── bot.py                 # Main bot application
│   ├── database.py            # Database management
│   ├── user_manager.py        # User registration and pairing
│   ├── appointment_manager.py # Appointment CRUD operations
│   ├── checklist_manager.py   # Checklist management
│   ├── openai_client.py       # OpenAI API integration
│   └── reminder_service.py    # Notification system
├── config/                    # Configuration files
├── data/                      # Database storage
├── logs/                      # Application logs
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## 📊 Database Schema

### Users Table
- `id` - Primary key
- `telegram_id` - Unique Telegram user ID
- `username` - Telegram username
- `first_name` - User's first name
- `last_name` - User's last name
- `paired_user_id` - ID of paired partner
- `created_at` - Registration timestamp

### Appointments Table
- `id` - Primary key
- `title` - Appointment title
- `description` - Detailed description
- `appointment_date` - Date and time
- `location` - Location information
- `created_by` - Creator user ID
- `shared_with` - Partner user ID
- `reminder_sent` - Reminder status
- `created_at` - Creation timestamp

### Checklists Table
- `id` - Primary key
- `title` - Checklist title
- `description` - Optional description
- `created_by` - Creator user ID
- `shared_with` - Partner user ID
- `created_at` - Creation timestamp

### Checklist Items Table
- `id` - Primary key
- `checklist_id` - Parent checklist ID
- `text` - Item description
- `completed` - Completion status
- `completed_by` - User who completed it
- `completed_at` - Completion timestamp
- `created_at` - Creation timestamp

## 🔧 Development

### Running in Development Mode

1. **Enable debug logging**
   ```env
   LOG_LEVEL=DEBUG
   ```

2. **Use test database**
   ```env
   DATABASE_PATH=data/test_cupidgpt.db
   ```

3. **Run with auto-reload** (install `python-dotenv`)
   ```bash
   python -m src.bot
   ```

### Testing

The bot includes comprehensive error handling and logging. Monitor the logs for debugging:

```bash
tail -f logs/cupidgpt.log
```

### Adding New Features

1. **Database Changes**: Update `database.py` with new tables/columns
2. **API Integration**: Extend `openai_client.py` for new AI features
3. **Bot Commands**: Add handlers in `bot.py`
4. **Business Logic**: Implement in respective manager classes

## 🚨 Troubleshooting

### Common Issues

#### Bot Not Responding
- Check if the bot token is correct
- Verify the bot is running (`python src/bot.py`)
- Check logs for error messages

#### OpenAI API Errors
- Verify API key is valid and has credits
- Check rate limits and usage quotas
- Monitor logs for specific error messages

#### Database Issues
- Ensure `data/` directory exists and is writable
- Check SQLite file permissions
- Review database initialization logs

#### Pairing Problems
- Both users must start the bot with `/start`
- Use exact Telegram username (without @)
- Check that neither user is already paired

### Debug Commands

Add these environment variables for verbose debugging:
```env
LOG_LEVEL=DEBUG
OPENAI_DEBUG=true
```

### Log Locations
- Application logs: `logs/cupidgpt.log`
- Error logs: Check console output
- Database logs: Included in main log file

## 📈 Performance & Scaling

### Database Optimization
- SQLite is suitable for small to medium usage
- For high traffic, consider PostgreSQL
- Regular database backups recommended

### API Rate Limits
- OpenAI API has usage limits
- Implement caching for repeated queries
- Monitor API usage in OpenAI dashboard

### Memory Usage
- Bot maintains minimal memory footprint
- Database connections are properly closed
- Consider process monitoring for production

## 🔒 Security Considerations

### Data Protection
- Environment variables for sensitive data
- SQLite database file permissions
- No hardcoded credentials in code

### API Security
- Secure API key storage
- Rate limiting on bot commands
- Input validation for all user data

### User Privacy
- Minimal data collection
- Secure partner pairing system
- Option to delete all user data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints to new functions
- Include logging for important operations
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [OpenAI](https://openai.com/) - Natural language processing
- [SQLite](https://www.sqlite.org/) - Database engine

## 📞 Support

For support, please:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub with details

---

**Made with ❤️ for couples who want to stay organized together!**