"""
Unit tests for appointment creation functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock


class TestCreateAppointmentFromText:
    """Test suite for create_appointment_from_text method."""
    
    @pytest.mark.asyncio
    async def test_successful_appointment_creation(self, appointment_manager, test_user, mock_llm_client):
        """Test successful appointment creation from natural language text."""
        # Arrange
        text = "Dinner tomorrow at 7pm at Mario's restaurant"
        
        # Act
        result = await appointment_manager.create_appointment_from_text(text, test_user)
        
        # Assert
        assert result['success'] is True
        assert 'appointment' in result
        assert result['appointment']['title'] == 'Test Appointment'
        assert result['appointment']['location'] == 'Test Location'
        assert result['message'] == 'Appointment created successfully'
        assert mock_llm_client.extract_appointment_details.called
    
    @pytest.mark.asyncio
    async def test_appointment_creation_with_past_date(self, appointment_manager, test_user, mock_llm_client):
        """Test that appointments cannot be created in the past."""
        # Arrange
        text = "Meeting yesterday at 3pm"
        past_datetime = datetime(2020, 1, 1, 15, 0).isoformat()
        
        mock_llm_client.extract_appointment_details = AsyncMock(return_value={
            'success': True,
            'title': 'Past Meeting',
            'description': 'This is in the past',
            'appointment_datetime': past_datetime,
            'location': 'Office',
            'duration_minutes': 60
        })
        
        # Act
        result = await appointment_manager.create_appointment_from_text(text, test_user)
        
        # Assert
        assert result['success'] is False
        assert 'past' in result['message'].lower()
    
    @pytest.mark.asyncio
    async def test_appointment_creation_llm_failure(self, appointment_manager, test_user, mock_llm_client):
        """Test handling of LLM extraction failure."""
        # Arrange
        text = "Some unclear text"
        
        mock_llm_client.extract_appointment_details = AsyncMock(return_value={
            'success': False,
            'error': 'Could not parse appointment details'
        })
        
        # Act
        result = await appointment_manager.create_appointment_from_text(text, test_user)
        
        # Assert
        assert result['success'] is False
        assert 'Failed to understand' in result['message'] or 'Could not parse' in result['message']
    
    @pytest.mark.asyncio
    async def test_appointment_creation_with_minimal_details(self, appointment_manager, test_user, mock_llm_client):
        """Test appointment creation with minimal details (no location, description)."""
        # Arrange
        text = "Meeting tomorrow at 2pm"
        
        mock_llm_client.extract_appointment_details = AsyncMock(return_value={
            'success': True,
            'title': 'Meeting',
            'description': '',
            'appointment_datetime': datetime(2026, 3, 1, 14, 0).isoformat(),
            'location': '',
            'duration_minutes': 60
        })
        
        # Act
        result = await appointment_manager.create_appointment_from_text(text, test_user)
        
        # Assert
        assert result['success'] is True
        assert result['appointment']['title'] == 'Meeting'
        assert result['appointment']['description'] == ''
        assert result['appointment']['location'] == ''
    
    @pytest.mark.asyncio
    async def test_appointment_creation_invalid_user(self, appointment_manager, mock_llm_client):
        """Test appointment creation with non-existent user."""
        # Arrange
        text = "Meeting tomorrow at 2pm"
        invalid_user_id = 999999999
        
        # Act
        result = await appointment_manager.create_appointment_from_text(text, invalid_user_id)
        
        # Assert
        assert result['success'] is False
        assert 'database' in result['message'].lower() or 'failed' in result['message'].lower()
    
    @pytest.mark.asyncio
    async def test_appointment_creation_with_exception(self, appointment_manager, test_user, mock_llm_client):
        """Test handling of unexpected exceptions during appointment creation."""
        # Arrange
        text = "Meeting tomorrow"
        
        mock_llm_client.extract_appointment_details = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        # Act
        result = await appointment_manager.create_appointment_from_text(text, test_user)
        
        # Assert
        assert result['success'] is False
        assert 'error' in result['message'].lower()


class TestCreateAppointmentManual:
    """Test suite for create_appointment_manual method."""
    
    @pytest.mark.asyncio
    async def test_successful_manual_appointment_creation(self, appointment_manager, test_user, future_datetime):
        """Test successful manual appointment creation."""
        # Arrange
        title = "Team Meeting"
        description = "Weekly team sync"
        location = "Conference Room A"
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title=title,
            description=description,
            appointment_date=future_datetime,
            location=location,
            user_telegram_id=test_user
        )
        
        # Assert
        assert result['success'] is True
        assert result['appointment']['title'] == title
        assert result['appointment']['description'] == description
        assert result['appointment']['location'] == location
        assert 'id' in result['appointment']
    
    @pytest.mark.asyncio
    async def test_manual_appointment_with_past_date(self, appointment_manager, test_user, past_datetime):
        """Test that manual appointments cannot be created in the past."""
        # Arrange
        title = "Past Meeting"
        description = "This should fail"
        location = "Office"
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title=title,
            description=description,
            appointment_date=past_datetime,
            location=location,
            user_telegram_id=test_user
        )
        
        # Assert
        assert result['success'] is False
        assert 'past' in result['message'].lower()
    
    @pytest.mark.asyncio
    async def test_manual_appointment_with_empty_title(self, appointment_manager, test_user, future_datetime):
        """Test manual appointment creation with empty title."""
        # Arrange
        title = ""
        description = "Meeting description"
        location = "Office"
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title=title,
            description=description,
            appointment_date=future_datetime,
            location=location,
            user_telegram_id=test_user
        )
        
        # Assert
        # SQLite allows empty strings even with NOT NULL constraint
        # In production, this should be validated at the application level
        assert result['success'] is True
        assert result['appointment']['title'] == ""
    
    @pytest.mark.asyncio
    async def test_manual_appointment_with_special_characters(self, appointment_manager, test_user, future_datetime):
        """Test manual appointment creation with special characters in fields."""
        # Arrange
        title = "Meeting with @John & Jane's Team"
        description = "Discuss Q1 results (50% increase!) & future plans"
        location = "Room #42 - 'Innovation Hub'"
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title=title,
            description=description,
            appointment_date=future_datetime,
            location=location,
            user_telegram_id=test_user
        )
        
        # Assert
        assert result['success'] is True
        assert result['appointment']['title'] == title
        assert result['appointment']['description'] == description
        assert result['appointment']['location'] == location
    
    @pytest.mark.asyncio
    async def test_manual_appointment_invalid_user(self, appointment_manager, future_datetime):
        """Test manual appointment creation with non-existent user."""
        # Arrange
        invalid_user_id = 999999999
        title = "Meeting"
        description = "Test"
        location = "Office"
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title=title,
            description=description,
            appointment_date=future_datetime,
            location=location,
            user_telegram_id=invalid_user_id
        )
        
        # Assert
        assert result['success'] is False


class TestAppointmentRetrieval:
    """Test suite for appointment retrieval methods."""
    
    @pytest.mark.asyncio
    async def test_get_user_appointments_empty(self, appointment_manager, test_user):
        """Test retrieving appointments when user has none."""
        # Act
        appointments = await appointment_manager.get_user_appointments(test_user)
        
        # Assert
        assert isinstance(appointments, list)
        assert len(appointments) == 0
    
    @pytest.mark.asyncio
    async def test_get_user_appointments_with_data(self, appointment_manager, test_user, future_datetime):
        """Test retrieving appointments when user has some."""
        # Arrange - Create an appointment first
        await appointment_manager.create_appointment_manual(
            title="Test Meeting",
            description="Test",
            appointment_date=future_datetime,
            location="Office",
            user_telegram_id=test_user
        )
        
        # Act
        appointments = await appointment_manager.get_user_appointments(test_user)
        
        # Assert
        assert len(appointments) == 1
        assert appointments[0]['title'] == "Test Meeting"
        assert 'formatted_date' in appointments[0]
        assert 'relative_time' in appointments[0]
    
    @pytest.mark.asyncio
    async def test_get_appointment_by_id(self, appointment_manager, test_user, future_datetime):
        """Test retrieving a specific appointment by ID."""
        # Arrange - Create an appointment first
        result = await appointment_manager.create_appointment_manual(
            title="Specific Meeting",
            description="Test",
            appointment_date=future_datetime,
            location="Office",
            user_telegram_id=test_user
        )
        
        appointment_id = result['appointment']['id']
        
        # Act
        appointment = await appointment_manager.get_appointment_by_id(appointment_id)
        
        # Assert
        assert appointment is not None
        assert appointment['id'] == appointment_id
        assert appointment['title'] == "Specific Meeting"
        assert 'creator_name' in appointment
    
    @pytest.mark.asyncio
    async def test_get_appointment_by_invalid_id(self, appointment_manager):
        """Test retrieving appointment with non-existent ID."""
        # Act
        appointment = await appointment_manager.get_appointment_by_id(999999)
        
        # Assert
        assert appointment is None


class TestAppointmentSharing:
    """Test suite for appointment sharing between paired users."""
    
    @pytest.mark.asyncio
    async def test_paired_users_see_shared_appointments(self, appointment_manager, test_paired_users, future_datetime):
        """Test that paired users can see each other's appointments."""
        # Arrange - User 1 creates an appointment
        result = await appointment_manager.create_appointment_manual(
            title="Shared Meeting",
            description="Both users should see this",
            appointment_date=future_datetime,
            location="Office",
            user_telegram_id=test_paired_users['user1']
        )
        
        # Act - User 2 retrieves appointments
        user2_appointments = await appointment_manager.get_user_appointments(test_paired_users['user2'])
        
        # Assert
        assert len(user2_appointments) == 1
        assert user2_appointments[0]['title'] == "Shared Meeting"
    
    @pytest.mark.asyncio
    async def test_unpaired_users_dont_see_appointments(self, appointment_manager, db_manager, test_user, future_datetime):
        """Test that unpaired users don't see each other's appointments."""
        # Arrange - Create another unpaired user
        other_user_id = 333333333
        db_manager.add_user(
            telegram_id=other_user_id,
            username='otheruser',
            first_name='Other',
            last_name='User'
        )
        
        # User 1 creates an appointment
        await appointment_manager.create_appointment_manual(
            title="Private Meeting",
            description="Only for user 1",
            appointment_date=future_datetime,
            location="Office",
            user_telegram_id=test_user
        )
        
        # Act - Other user tries to retrieve appointments
        other_appointments = await appointment_manager.get_user_appointments(other_user_id)
        
        # Assert
        assert len(other_appointments) == 0


class TestAppointmentEdgeCases:
    """Test suite for edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_appointment_at_exact_current_time(self, appointment_manager, test_user):
        """Test creating appointment at exactly the current time."""
        # Arrange
        current_time = datetime.now()
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title="Right Now Meeting",
            description="At current time",
            appointment_date=current_time,
            location="Office",
            user_telegram_id=test_user
        )
        
        # Assert - Should fail as it's technically in the past
        assert result['success'] is False
    
    @pytest.mark.asyncio
    async def test_very_long_title_and_description(self, appointment_manager, test_user, future_datetime):
        """Test appointment with very long title and description."""
        # Arrange
        long_title = "A" * 500
        long_description = "B" * 5000
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title=long_title,
            description=long_description,
            appointment_date=future_datetime,
            location="Office",
            user_telegram_id=test_user
        )
        
        # Assert
        assert result['success'] is True
        assert result['appointment']['title'] == long_title
        assert result['appointment']['description'] == long_description
    
    @pytest.mark.asyncio
    async def test_unicode_characters_in_appointment(self, appointment_manager, test_user, future_datetime):
        """Test appointment with unicode characters."""
        # Arrange
        title = "Meeting with 日本 🎉"
        description = "Discuss café plans ☕ and résumé 📄"
        location = "Zürich, Café Français"
        
        # Act
        result = await appointment_manager.create_appointment_manual(
            title=title,
            description=description,
            appointment_date=future_datetime,
            location=location,
            user_telegram_id=test_user
        )
        
        # Assert
        assert result['success'] is True
        assert result['appointment']['title'] == title
        assert result['appointment']['description'] == description
        assert result['appointment']['location'] == location
    
    @pytest.mark.asyncio
    async def test_multiple_appointments_same_time(self, appointment_manager, test_user, future_datetime):
        """Test creating multiple appointments at the same time."""
        # Arrange & Act - Create two appointments at the same time
        result1 = await appointment_manager.create_appointment_manual(
            title="Meeting 1",
            description="First meeting",
            appointment_date=future_datetime,
            location="Room A",
            user_telegram_id=test_user
        )
        
        result2 = await appointment_manager.create_appointment_manual(
            title="Meeting 2",
            description="Second meeting",
            appointment_date=future_datetime,
            location="Room B",
            user_telegram_id=test_user
        )
        
        # Assert - Both should succeed (no conflict checking in creation)
        assert result1['success'] is True
        assert result2['success'] is True
        
        # Verify both exist
        appointments = await appointment_manager.get_user_appointments(test_user)
        assert len(appointments) == 2
