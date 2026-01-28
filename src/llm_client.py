import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
import re
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class LLMClient:
    """Handles Google Gemini API interactions for natural language processing."""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    
    async def determine_intent(self, text: str) -> Dict[str, Any]:
        """Determine the user's intent from natural language text."""
        try:
            prompt = f"""
Analyze the following text and determine if the user wants to:
1. Create an appointment/meeting/event
2. Create a checklist/todo list
3. Something else

Text: "{text}"

Respond with JSON in this format:
{{
    "type": "appointment" | "checklist" | "unknown",
    "confidence": 0.0-1.0,
    "reason": "brief explanation"
}}

Examples:
- "Dinner tomorrow at 7pm" -> appointment
- "Buy milk, bread, eggs" -> checklist  
- "Meeting with John on Friday" -> appointment
- "Grocery list: apples, bananas" -> checklist
"""
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.1},
                safety_settings=self.safety_settings
            )
            
            result = json.loads(response.text)
            return result
            
        except Exception as e:
            logging.error(f"Error determining intent: {e}")
            return {"type": "unknown", "confidence": 0.0, "reason": "Error processing"}
    
    async def extract_appointment_details(self, text: str) -> Dict[str, Any]:
        """Extract appointment details from natural language text."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            prompt = f"""
Extract appointment details from the following text. Current date/time: {current_date}

Text: "{text}"

Extract and return JSON with these fields:
{{
    "title": "brief title for the appointment",
    "description": "detailed description (optional)",
    "date": "YYYY-MM-DD",
    "time": "HH:MM (24-hour format)",
    "location": "location if mentioned",
    "duration_minutes": estimated duration in minutes,
    "success": true/false,
    "error": "error message if parsing failed"
}}

Rules:
- If no specific date is mentioned, assume today
- If "tomorrow" is mentioned, use tomorrow's date
- If day of week is mentioned (e.g., "Friday"), use the next occurrence
- If no time is specified, suggest a reasonable time
- If location is not specified, set to null
- Title should be concise (2-5 words)
- Description can include additional context

Examples:
"Dinner at Mario's restaurant tomorrow at 7pm" ->
{{
    "title": "Dinner at Mario's",
    "description": "Dinner at Mario's restaurant",
    "date": "2024-01-16",
    "time": "19:00",
    "location": "Mario's restaurant",
    "duration_minutes": 120,
    "success": true,
    "error": null
}}
"""
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.1},
                safety_settings=self.safety_settings
            )
            
            result = json.loads(response.text)
            
            # Validate and format the result
            if result.get('success'):
                # Combine date and time into datetime string
                date_str = result.get('date', '')
                time_str = result.get('time', '12:00')
                
                try:
                    appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    result['appointment_datetime'] = appointment_datetime.isoformat()
                except ValueError as e:
                    result['success'] = False
                    result['error'] = f"Invalid date/time format: {e}"
            
            return result
            
        except Exception as e:
            logging.error(f"Error extracting appointment details: {e}")
            return {
                "success": False,
                "error": f"Failed to process appointment: {str(e)}"
            }
    
    async def extract_checklist_details(self, text: str) -> Dict[str, Any]:
        """Extract checklist details from natural language text."""
        try:
            prompt = f"""
Extract checklist information from the following text:

Text: "{text}"

Return JSON with these fields:
{{
    "title": "checklist title",
    "description": "optional description",
    "items": ["item1", "item2", "item3"],
    "success": true/false,
    "error": "error message if parsing failed"
}}

Rules:
- Extract a clear, concise title for the checklist
- Identify individual items/tasks
- Items can be separated by commas, newlines, or bullet points
- Remove any list formatting (bullets, numbers, etc.)
- Each item should be a simple task or item name
- Minimum 1 item required for success

Examples:
"Grocery Shopping\\nMilk\\nBread\\nEggs\\nApples" ->
{{
    "title": "Grocery Shopping",
    "description": null,
    "items": ["Milk", "Bread", "Eggs", "Apples"],
    "success": true,
    "error": null
}}

"Buy milk, bread, and eggs for tomorrow" ->
{{
    "title": "Shopping List",
    "description": "Items needed for tomorrow",
    "items": ["Milk", "Bread", "Eggs"],
    "success": true,
    "error": null
}}
"""
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.1},
                safety_settings=self.safety_settings
            )
            
            result = json.loads(response.text)
            
            # Validate result
            if result.get('success'):
                items = result.get('items', [])
                if not items or len(items) == 0:
                    result['success'] = False
                    result['error'] = "No checklist items found"
                else:
                    # Clean up items
                    cleaned_items = []
                    for item in items:
                        cleaned_item = item.strip().rstrip('.,;:')
                        if cleaned_item:
                            cleaned_items.append(cleaned_item)
                    result['items'] = cleaned_items
            
            return result
            
        except Exception as e:
            logging.error(f"Error extracting checklist details: {e}")
            return {
                "success": False,
                "error": f"Failed to process checklist: {str(e)}"
            }
    
    async def parse_date_time(self, text: str) -> Optional[datetime]:
        """Parse natural language date/time expressions."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            prompt = f"""
Parse the date and time from this text. Current date/time: {current_date}

Text: "{text}"

Return JSON:
{{
    "datetime": "YYYY-MM-DD HH:MM",
    "success": true/false,
    "confidence": 0.0-1.0
}}

Handle expressions like:
- "tomorrow at 3pm"
- "next Friday at 2:30"
- "in 2 hours"
- "January 15th at 9am"
- "tonight at 8"
"""
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.1},
                safety_settings=self.safety_settings
            )
            
            result = json.loads(response.text)
            
            if result.get('success') and result.get('datetime'):
                return datetime.strptime(result['datetime'], "%Y-%m-%d %H:%M")
            
            return None
            
        except Exception as e:
            logging.error(f"Error parsing date/time: {e}")
            return None
    
    async def extract_links_info(self, text: str) -> Dict[str, Any]:
        """Extract information from links in the text."""
        try:
            # Find URLs in text
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, text)
            
            if not urls:
                return {"links": [], "success": True}
            
            # For now, just return the URLs found
            return {
                "links": urls,
                "success": True,
                "extracted_info": f"Found {len(urls)} link(s) in the message"
            }
            
        except Exception as e:
            logging.error(f"Error extracting links info: {e}")
            return {"links": [], "success": False, "error": str(e)}
    
    async def suggest_appointment_improvements(self, appointment_data: Dict[str, Any]) -> str:
        """Suggest improvements for an appointment."""
        try:
            prompt = f"""
Review this appointment and suggest improvements:

Title: {appointment_data.get('title')}
Description: {appointment_data.get('description')}
Date/Time: {appointment_data.get('appointment_date')}
Location: {appointment_data.get('location')}

Provide brief suggestions for:
1. Better title (if needed)
2. Missing important details
3. Potential scheduling conflicts
4. Location specificity

Keep response under 100 words.
"""
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"temperature": 0.3},
                safety_settings=self.safety_settings
            )
            
            return response.text
            
        except Exception as e:
            logging.error(f"Error suggesting appointment improvements: {e}")
            return "No suggestions available at this time."