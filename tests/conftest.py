"""
Pytest configuration and fixtures for CupidGPT tests.
"""
import pytest
import os
import sys
import tempfile
import sqlite3
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import DatabaseManager
from llm_client import LLMClient
from appointment_manager import AppointmentManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager instance with a temporary database."""
    return DatabaseManager(temp_db)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = MagicMock(spec=LLMClient)
    
    # Default successful appointment extraction
    async def mock_extract_appointment_details(text):
        return {
            'success': True,
            'title': 'Test Appointment',
            'description': 'Test description',
            'appointment_datetime': datetime(2026, 3, 1, 14, 0).isoformat(),
            'location': 'Test Location',
            'duration_minutes': 60
        }
    
    client.extract_appointment_details = AsyncMock(side_effect=mock_extract_appointment_details)
    
    return client


@pytest.fixture
def appointment_manager(db_manager, mock_llm_client):
    """Create an AppointmentManager instance with mocked dependencies."""
    return AppointmentManager(db_manager, mock_llm_client)


@pytest.fixture
def test_user(db_manager):
    """Create a test user in the database."""
    telegram_id = 123456789
    db_manager.add_user(
        telegram_id=telegram_id,
        username='testuser',
        first_name='Test',
        last_name='User'
    )
    return telegram_id


@pytest.fixture
def test_paired_users(db_manager):
    """Create two paired test users in the database."""
    user1_telegram_id = 111111111
    user2_telegram_id = 222222222
    
    db_manager.add_user(
        telegram_id=user1_telegram_id,
        username='user1',
        first_name='User',
        last_name='One'
    )
    
    db_manager.add_user(
        telegram_id=user2_telegram_id,
        username='user2',
        first_name='User',
        last_name='Two'
    )
    
    db_manager.pair_users(user1_telegram_id, user2_telegram_id)
    
    return {
        'user1': user1_telegram_id,
        'user2': user2_telegram_id
    }


@pytest.fixture
def future_datetime():
    """Return a datetime in the future for testing."""
    return datetime(2026, 12, 31, 15, 30)


@pytest.fixture
def past_datetime():
    """Return a datetime in the past for testing."""
    return datetime(2020, 1, 1, 10, 0)
