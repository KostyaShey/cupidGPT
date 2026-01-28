"""
Tests for LLM client appointment extraction functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from src.llm_client import LLMClient


class TestLLMAppointmentExtraction:
    """Test suite for LLM-based appointment detail extraction."""
    
    @pytest.fixture
    def llm_client(self):
        """Create a real LLM client instance (will be mocked)."""
        return LLMClient(api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_extract_simple_appointment(self, llm_client):
        """Test extraction of simple appointment details."""
        # Arrange
        text = "Dinner tomorrow at 7pm"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "title": "Dinner",
            "description": "Dinner tomorrow evening",
            "date": "2026-01-29",
            "time": "19:00",
            "location": null,
            "duration_minutes": 120,
            "success": true,
            "error": null
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.extract_appointment_details(text)
            
            # Assert
            assert result['success'] is True
            assert result['title'] == "Dinner"
            assert 'appointment_datetime' in result
    
    @pytest.mark.asyncio
    async def test_extract_appointment_with_location(self, llm_client):
        """Test extraction with location information."""
        # Arrange
        text = "Meeting at Starbucks on Main Street tomorrow at 3pm"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "title": "Meeting at Starbucks",
            "description": "Meeting at Starbucks on Main Street",
            "date": "2026-01-29",
            "time": "15:00",
            "location": "Starbucks on Main Street",
            "duration_minutes": 60,
            "success": true,
            "error": null
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.extract_appointment_details(text)
            
            # Assert
            assert result['success'] is True
            assert result['location'] == "Starbucks on Main Street"
    
    @pytest.mark.asyncio
    async def test_extract_appointment_with_relative_date(self, llm_client):
        """Test extraction with relative date expressions."""
        # Arrange
        text = "Team meeting next Friday at 10am"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "title": "Team Meeting",
            "description": "Team meeting",
            "date": "2026-01-31",
            "time": "10:00",
            "location": null,
            "duration_minutes": 60,
            "success": true,
            "error": null
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.extract_appointment_details(text)
            
            # Assert
            assert result['success'] is True
            assert result['title'] == "Team Meeting"
    
    @pytest.mark.asyncio
    async def test_extract_appointment_failure(self, llm_client):
        """Test handling of extraction failure."""
        # Arrange
        text = "Some unclear text that doesn't describe an appointment"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "title": null,
            "description": null,
            "date": null,
            "time": null,
            "location": null,
            "duration_minutes": null,
            "success": false,
            "error": "Could not identify appointment details"
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.extract_appointment_details(text)
            
            # Assert
            assert result['success'] is False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_extract_appointment_with_duration(self, llm_client):
        """Test extraction with explicit duration."""
        # Arrange
        text = "2-hour workshop tomorrow at 2pm"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "title": "Workshop",
            "description": "2-hour workshop",
            "date": "2026-01-29",
            "time": "14:00",
            "location": null,
            "duration_minutes": 120,
            "success": true,
            "error": null
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.extract_appointment_details(text)
            
            # Assert
            assert result['success'] is True
            assert result['duration_minutes'] == 120
    
    @pytest.mark.asyncio
    async def test_extract_appointment_invalid_date_format(self, llm_client):
        """Test handling of invalid date format from LLM."""
        # Arrange
        text = "Meeting tomorrow"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "title": "Meeting",
            "description": "Meeting",
            "date": "invalid-date",
            "time": "10:00",
            "location": null,
            "duration_minutes": 60,
            "success": true,
            "error": null
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.extract_appointment_details(text)
            
            # Assert
            assert result['success'] is False
            assert 'Invalid date/time format' in result['error']
    
    @pytest.mark.asyncio
    async def test_extract_appointment_api_exception(self, llm_client):
        """Test handling of API exceptions."""
        # Arrange
        text = "Meeting tomorrow"
        
        with patch.object(llm_client.model, 'generate_content_async', 
                         new=AsyncMock(side_effect=Exception("API Error"))):
            # Act
            result = await llm_client.extract_appointment_details(text)
            
            # Assert
            assert result['success'] is False
            assert 'error' in result


class TestLLMIntentDetermination:
    """Test suite for intent determination."""
    
    @pytest.fixture
    def llm_client(self):
        """Create a real LLM client instance (will be mocked)."""
        return LLMClient(api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_determine_appointment_intent(self, llm_client):
        """Test identifying appointment intent."""
        # Arrange
        text = "Schedule a meeting with John tomorrow"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "type": "appointment",
            "confidence": 0.95,
            "reason": "Text mentions scheduling a meeting"
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.determine_intent(text)
            
            # Assert
            assert result['type'] == 'appointment'
            assert result['confidence'] > 0.9
    
    @pytest.mark.asyncio
    async def test_determine_checklist_intent(self, llm_client):
        """Test identifying checklist intent."""
        # Arrange
        text = "Buy milk, bread, and eggs"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "type": "checklist",
            "confidence": 0.92,
            "reason": "Text contains a list of items"
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.determine_intent(text)
            
            # Assert
            assert result['type'] == 'checklist'
            assert result['confidence'] > 0.9
    
    @pytest.mark.asyncio
    async def test_determine_unknown_intent(self, llm_client):
        """Test handling of unclear intent."""
        # Arrange
        text = "Hello, how are you?"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "type": "unknown",
            "confidence": 0.3,
            "reason": "Text is a greeting, not a task"
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.determine_intent(text)
            
            # Assert
            assert result['type'] == 'unknown'
            assert result['confidence'] < 0.5


class TestDateTimeParsing:
    """Test suite for date/time parsing."""
    
    @pytest.fixture
    def llm_client(self):
        """Create a real LLM client instance (will be mocked)."""
        return LLMClient(api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_parse_relative_datetime(self, llm_client):
        """Test parsing relative date/time expressions."""
        # Arrange
        text = "tomorrow at 3pm"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "datetime": "2026-01-29 15:00",
            "success": true,
            "confidence": 0.98
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.parse_date_time(text)
            
            # Assert
            assert result is not None
            assert isinstance(result, datetime)
    
    @pytest.mark.asyncio
    async def test_parse_absolute_datetime(self, llm_client):
        """Test parsing absolute date/time."""
        # Arrange
        text = "January 30th at 2:30pm"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "datetime": "2026-01-30 14:30",
            "success": true,
            "confidence": 0.99
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.parse_date_time(text)
            
            # Assert
            assert result is not None
            assert result.month == 1
            assert result.day == 30
    
    @pytest.mark.asyncio
    async def test_parse_datetime_failure(self, llm_client):
        """Test handling of parsing failure."""
        # Arrange
        text = "sometime maybe"
        
        mock_response = MagicMock()
        mock_response.text = '''{
            "datetime": null,
            "success": false,
            "confidence": 0.1
        }'''
        
        with patch.object(llm_client.model, 'generate_content_async', new=AsyncMock(return_value=mock_response)):
            # Act
            result = await llm_client.parse_date_time(text)
            
            # Assert
            assert result is None
