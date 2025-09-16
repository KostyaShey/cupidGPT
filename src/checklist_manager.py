import logging
from typing import Dict, Any, List, Optional
from database import DatabaseManager
from openai_client import OpenAIClient


class ChecklistManager:
    """Manages checklist creation, item management, and operations."""
    
    def __init__(self, db: DatabaseManager, openai_client: OpenAIClient):
        self.db = db
        self.openai_client = openai_client
    
    async def create_checklist_from_text(self, text: str, user_telegram_id: int) -> Dict[str, Any]:
        """Create a checklist from natural language text."""
        try:
            # Extract checklist details using OpenAI
            details = await self.openai_client.extract_checklist_details(text)
            
            if not details.get('success'):
                return {
                    'success': False,
                    'message': details.get('error', 'Failed to understand checklist details')
                }
            
            # Create the checklist
            checklist_id = self.db.create_checklist(
                title=details['title'],
                description=details.get('description', ''),
                created_by_telegram_id=user_telegram_id
            )
            
            if not checklist_id:
                return {
                    'success': False,
                    'message': 'Failed to create checklist in database'
                }
            
            # Add items to the checklist
            items_added = []
            for item_text in details['items']:
                if self.db.add_checklist_item(checklist_id, item_text):
                    items_added.append(item_text)
                else:
                    logging.warning(f"Failed to add item '{item_text}' to checklist {checklist_id}")
            
            if not items_added:
                return {
                    'success': False,
                    'message': 'Failed to add any items to the checklist'
                }
            
            checklist_data = {
                'id': checklist_id,
                'title': details['title'],
                'description': details.get('description', ''),
                'items_count': len(items_added)
            }
            
            logging.info(f"Checklist created: {checklist_id} by user {user_telegram_id} with {len(items_added)} items")
            
            return {
                'success': True,
                'checklist': checklist_data,
                'items': items_added,
                'message': f'Checklist created with {len(items_added)} items'
            }
            
        except Exception as e:
            logging.error(f"Error creating checklist from text: {e}")
            return {
                'success': False,
                'message': 'An error occurred while creating the checklist'
            }
    
    async def create_checklist_manual(self, title: str, description: str,
                                    items: List[str], user_telegram_id: int) -> Dict[str, Any]:
        """Create a checklist with manual input."""
        try:
            if not items:
                return {
                    'success': False,
                    'message': 'Checklist must have at least one item'
                }
            
            # Create the checklist
            checklist_id = self.db.create_checklist(
                title=title,
                description=description,
                created_by_telegram_id=user_telegram_id
            )
            
            if not checklist_id:
                return {
                    'success': False,
                    'message': 'Failed to create checklist in database'
                }
            
            # Add items to the checklist
            items_added = []
            for item_text in items:
                if self.db.add_checklist_item(checklist_id, item_text.strip()):
                    items_added.append(item_text.strip())
            
            checklist_data = {
                'id': checklist_id,
                'title': title,
                'description': description,
                'items_count': len(items_added)
            }
            
            logging.info(f"Manual checklist created: {checklist_id} by user {user_telegram_id}")
            
            return {
                'success': True,
                'checklist': checklist_data,
                'items': items_added,
                'message': f'Checklist created with {len(items_added)} items'
            }
            
        except Exception as e:
            logging.error(f"Error creating manual checklist: {e}")
            return {
                'success': False,
                'message': 'An error occurred while creating the checklist'
            }
    
    async def get_user_checklists(self, user_telegram_id: int) -> List[Dict[str, Any]]:
        """Get checklists for a user."""
        try:
            checklists = self.db.get_checklists(user_telegram_id)
            
            # Add item counts and completion statistics
            for checklist in checklists:
                items = self.db.get_checklist_items(checklist['id'])
                checklist['total_items'] = len(items)
                checklist['completed_items'] = len([item for item in items if item['completed']])
                checklist['completion_percentage'] = (
                    (checklist['completed_items'] / checklist['total_items'] * 100)
                    if checklist['total_items'] > 0 else 0
                )
            
            return checklists
            
        except Exception as e:
            logging.error(f"Error getting user checklists: {e}")
            return []
    
    async def get_checklist_items(self, checklist_id: int) -> List[Dict[str, Any]]:
        """Get items for a specific checklist."""
        try:
            return self.db.get_checklist_items(checklist_id)
        except Exception as e:
            logging.error(f"Error getting checklist items: {e}")
            return []
    
    async def get_checklist_by_id(self, checklist_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific checklist by ID."""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, u.first_name as creator_name
                    FROM checklists c
                    JOIN users u ON c.created_by = u.id
                    WHERE c.id = ?
                """, (checklist_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logging.error(f"Error getting checklist by ID: {e}")
            return None
    
    def toggle_item(self, item_id: int, user_telegram_id: int) -> bool:
        """Toggle completion status of a checklist item."""
        try:
            return self.db.toggle_checklist_item(item_id, user_telegram_id)
        except Exception as e:
            logging.error(f"Error toggling checklist item: {e}")
            return False
    
    async def add_item_to_checklist(self, checklist_id: int, item_text: str,
                                   user_telegram_id: int) -> Dict[str, Any]:
        """Add a new item to an existing checklist."""
        try:
            # Check if user has permission to modify this checklist
            checklist = await self.get_checklist_by_id(checklist_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found'
                }
            
            # Check if user is creator or shared user
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            user_id = user['id']
            if checklist['created_by'] != user_id and checklist.get('shared_with') != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to modify this checklist'
                }
            
            # Add the item
            success = self.db.add_checklist_item(checklist_id, item_text.strip())
            
            if success:
                logging.info(f"Item added to checklist {checklist_id} by user {user_telegram_id}")
                return {
                    'success': True,
                    'message': 'Item added successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to add item to checklist'
                }
                
        except Exception as e:
            logging.error(f"Error adding item to checklist: {e}")
            return {
                'success': False,
                'message': 'An error occurred while adding the item'
            }
    
    async def remove_item_from_checklist(self, item_id: int, user_telegram_id: int) -> Dict[str, Any]:
        """Remove an item from a checklist."""
        try:
            # Get item and checklist info
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ci.checklist_id, c.created_by, c.shared_with
                    FROM checklist_items ci
                    JOIN checklists c ON ci.checklist_id = c.id
                    WHERE ci.id = ?
                """, (item_id,))
                
                result = cursor.fetchone()
                if not result:
                    return {
                        'success': False,
                        'message': 'Item not found'
                    }
                
                checklist_id, created_by, shared_with = result
            
            # Check permissions
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            user_id = user['id']
            if created_by != user_id and shared_with != user_id:
                return {
                    'success': False,
                    'message': 'You do not have permission to modify this checklist'
                }
            
            # Remove the item
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
                conn.commit()
            
            logging.info(f"Item {item_id} removed from checklist {checklist_id} by user {user_telegram_id}")
            
            return {
                'success': True,
                'message': 'Item removed successfully'
            }
            
        except Exception as e:
            logging.error(f"Error removing item from checklist: {e}")
            return {
                'success': False,
                'message': 'An error occurred while removing the item'
            }
    
    async def delete_checklist(self, checklist_id: int, user_telegram_id: int) -> Dict[str, Any]:
        """Delete a checklist."""
        try:
            # Check if user has permission to delete this checklist
            checklist = await self.get_checklist_by_id(checklist_id)
            if not checklist:
                return {
                    'success': False,
                    'message': 'Checklist not found'
                }
            
            # Check if user is creator
            user = self.db.get_user_by_telegram_id(user_telegram_id)
            if not user:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            if checklist['created_by'] != user['id']:
                return {
                    'success': False,
                    'message': 'Only the creator can delete a checklist'
                }
            
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                # Delete checklist (items will be deleted due to CASCADE)
                cursor.execute("DELETE FROM checklists WHERE id = ?", (checklist_id,))
                conn.commit()
            
            logging.info(f"Checklist {checklist_id} deleted by user {user_telegram_id}")
            
            return {
                'success': True,
                'message': 'Checklist deleted successfully'
            }
            
        except Exception as e:
            logging.error(f"Error deleting checklist: {e}")
            return {
                'success': False,
                'message': 'An error occurred while deleting the checklist'
            }
    
    async def get_checklist_summary(self, checklist_id: int) -> str:
        """Get a formatted summary of a checklist."""
        try:
            checklist = await self.get_checklist_by_id(checklist_id)
            if not checklist:
                return "Checklist not found"
            
            items = await self.get_checklist_items(checklist_id)
            
            summary = f"📋 **{checklist['title']}**\n"
            if checklist.get('description'):
                summary += f"📝 {checklist['description']}\n"
            
            summary += f"\n📊 Progress: {len([i for i in items if i['completed']])}/{len(items)} items completed\n\n"
            
            for item in items:
                status = "✅" if item['completed'] else "⬜"
                summary += f"{status} {item['text']}\n"
                if item['completed'] and item.get('completed_by_name'):
                    summary += f"   └ Completed by {item['completed_by_name']}\n"
            
            return summary
            
        except Exception as e:
            logging.error(f"Error getting checklist summary: {e}")
            return "Error generating checklist summary"
    
    async def export_checklist(self, checklist_id: int, format_type: str = 'text') -> str:
        """Export a checklist in various formats."""
        try:
            checklist = await self.get_checklist_by_id(checklist_id)
            if not checklist:
                return "Checklist not found"
            
            items = await self.get_checklist_items(checklist_id)
            
            if format_type == 'text':
                export_text = f"📋 {checklist['title']}\n"
                if checklist.get('description'):
                    export_text += f"📝 {checklist['description']}\n"
                export_text += "\n"
                
                for i, item in enumerate(items, 1):
                    status = "[x]" if item['completed'] else "[ ]"
                    export_text += f"{i}. {status} {item['text']}\n"
                
                return export_text
            
            elif format_type == 'markdown':
                export_text = f"# {checklist['title']}\n\n"
                if checklist.get('description'):
                    export_text += f"{checklist['description']}\n\n"
                
                for item in items:
                    status = "- [x]" if item['completed'] else "- [ ]"
                    export_text += f"{status} {item['text']}\n"
                
                return export_text
            
            return "Export format not supported"
            
        except Exception as e:
            logging.error(f"Error exporting checklist: {e}")
            return "Error exporting checklist"
    
    async def get_completion_stats(self, user_telegram_id: int) -> Dict[str, Any]:
        """Get completion statistics for a user's checklists."""
        try:
            checklists = await self.get_user_checklists(user_telegram_id)
            
            total_checklists = len(checklists)
            total_items = sum(cl['total_items'] for cl in checklists)
            completed_items = sum(cl['completed_items'] for cl in checklists)
            completed_checklists = len([cl for cl in checklists if cl['completion_percentage'] == 100])
            
            return {
                'total_checklists': total_checklists,
                'completed_checklists': completed_checklists,
                'total_items': total_items,
                'completed_items': completed_items,
                'overall_completion_percentage': (
                    (completed_items / total_items * 100) if total_items > 0 else 0
                )
            }
            
        except Exception as e:
            logging.error(f"Error getting completion stats: {e}")
            return {
                'total_checklists': 0,
                'completed_checklists': 0,
                'total_items': 0,
                'completed_items': 0,
                'overall_completion_percentage': 0
            }