#!/usr/bin/env python3
"""
Setup script for CupidGPT Bot
This script helps with initial setup and configuration.
"""

import os
import sys
import subprocess
from pathlib import Path


def create_directories():
    """Create necessary directories."""
    directories = ['data', 'logs', 'config']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version compatible: {sys.version}")
    return True


def create_env_file():
    """Create .env file from template if it doesn't exist."""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            subprocess.run(['cp', '.env.example', '.env'])
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env file with your API keys!")
        else:
            print("❌ .env.example not found!")
    else:
        print("✅ .env file already exists")


def install_dependencies():
    """Install Python dependencies."""
    try:
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies!")
        return False
    return True


def test_imports():
    """Test if all required modules can be imported."""
    required_modules = [
        'telegram',
        'openai',
        'sqlite3',
        'schedule',
        'dotenv'
    ]
    
    failed_imports = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} imported successfully")
        except ImportError:
            print(f"❌ Failed to import {module}")
            failed_imports.append(module)
    
    return len(failed_imports) == 0


def initialize_database():
    """Initialize the database."""
    try:
        from src.database import DatabaseManager
        db = DatabaseManager('data/cupidgpt.db')
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False


def validate_env_file():
    """Validate .env file has required variables."""
    required_vars = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        return False
    
    with open('.env', 'r') as f:
        content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if f"{var}=your_" in content or var not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Please configure these variables in .env: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment variables configured")
    return True


def main():
    """Main setup function."""
    print("🚀 CupidGPT Bot Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Test imports
    if not test_imports():
        print("❌ Some modules failed to import. Please check your installation.")
        return False
    
    # Initialize database
    if not initialize_database():
        return False
    
    # Validate environment
    env_valid = validate_env_file()
    
    print("\n" + "=" * 40)
    print("🎉 Setup completed!")
    
    if env_valid:
        print("\n✅ Ready to start the bot:")
        print("   python src/bot.py")
    else:
        print("\n⚠️  Next steps:")
        print("   1. Edit .env file with your API keys")
        print("   2. Run: python src/bot.py")
    
    print("\n📚 Documentation: README.md")
    print("🆘 Support: Check the troubleshooting section in README.md")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)