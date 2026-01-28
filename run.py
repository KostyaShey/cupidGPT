#!/usr/bin/env python3
"""
Simple run script for CupidGPT Bot
Checks configuration and starts the bot.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_configuration():
    """Check if bot is properly configured."""
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Run setup.py first: python setup.py")
        return False
    
    # Check for required environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'GEMINI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Please configure these variables in .env: {', '.join(missing_vars)}")
        return False
    
    return True

def main():
    """Main run function."""
    print("🚀 Starting CupidGPT Bot...")
    
    if not check_configuration():
        print("\n💡 Run setup.py first if this is your first time:")
        print("   python setup.py")
        return False
    
    try:
        # Import and run the bot
        from bot import CupidGPTBot
        bot = CupidGPTBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)