
"""
Notion AI Agent - Main Script
A simple AI agent that connects to Notion and uses local models
"""

import os
import sys
import json
from typing import Dict, Any, List
from notion_client import Client

from base_agent import BaseAgent

class NotionAgent(BaseAgent):
    """Notion AI Agent for workspace management"""

    def __init__(self):
        super().__init__("notion")
        self.notion_token = os.getenv('NOTION_TOKEN')
        if not self.notion_token:
            self.logger.error("NOTION_TOKEN not found in .env file")
            raise ValueError("NOTION_TOKEN not found")
        
        self.notion = Client(auth=self.notion_token)

    def _test_service_connection(self) -> bool:
        """Test if Notion connection works"""
        try:
            databases = self.notion.search(filter={"property": "object", "value": "database"})
            self.logger.info(f"Connected to Notion! Found {len(databases['results'])} databases")
            return True
        except Exception as e:
            self.logger.error(f"Notion connection failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent"""
        try:
            databases = self.get_databases()
            return {
                'status': 'connected',
                'database_count': len(databases)
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def get_databases(self) -> List[Dict[str, Any]]:
        """Get all accessible databases"""
        try:
            databases = self.notion.search(filter={"property": "object", "value": "database"})
            return databases.get('results', [])
        except Exception as e:
            self.logger.error(f"Error getting databases: {e}")
            return []

    def get_database_pages(self, database_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pages from a specific database"""
        try:
            pages = self.notion.databases.query(
                database_id=database_id,
                page_size=limit
            )
            return pages.get('results', [])
        except Exception as e:
            self.logger.error(f"Error getting pages: {e}")
            return []

    def ask_about_notion(self, question: str) -> str:
        """Ask AI about Notion data with context"""
        databases = self.get_databases()
        
        context = f"""
        You are an AI assistant that has access to a user's Notion workspace. 
        
        Current Notion workspace contains:
        - {len(databases)} databases
        
        Database details:
        """
        
        for db in databases:
            title = db.get('title', [{}])[0].get('text', {}).get('content', 'Untitled')
            pages = self.get_database_pages(db['id'], limit=5)
            context += f"\n- Database: '{title}' (ID: {db['id']}) with {len(pages)} pages"
        
        context += f"\n\nUser question: {question}"
        context += "\n\nPlease answer based on the Notion data provided above. If you need more specific information about a database, suggest using the 'summarize' command."
        
        self.log_action("ask_about_notion", f"Answering question: {question}")
        return self.ask_ai(context)

    def summarize_database(self, database_id: str) -> str:
        """Summarize content of a database using AI"""
        pages = self.get_database_pages(database_id)
        if not pages:
            return "No pages found in database"
        
        page_info = []
        for page in pages:
            title = "Untitled"
            if page.get('properties'):
                for prop_name, prop_value in page['properties'].items():
                    if prop_value['type'] == 'title' and prop_value.get('title'):
                        title = prop_value['title'][0]['text']['content']
                        break
            
            page_info.append({
                'title': title,
                'created': page['created_time'],
                'last_edited': page['last_edited_time']
            })
        
        prompt = f"""
        I have a Notion database with {len(pages)} pages. Here's the information:
        
        {json.dumps(page_info, indent=2)}
        
        Please provide a brief summary of this database content and suggest what type of database this might be.
        """
        
        self.log_action("summarize_database", f"Summarizing database ID: {database_id}")
        return self.ask_ai(prompt)

    def interactive_mode(self):
        """Interactive CLI mode"""
        print("\n🤖 Notion AI Agent - Interactive Mode")
        print("Commands: 'databases', 'summarize <db_id>', 'ask <question>', 'quit'")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if command == 'quit':
                    print("Goodbye!")
                    break
                elif command == 'databases':
                    databases = self.get_databases()
                    if databases:
                        print("\n📊 Available databases:")
                        for i, db in enumerate(databases, 1):
                            title = db.get('title', [{}])[0].get('text', {}).get('content', 'Untitled')
                            print(f"{i}. {title} (ID: {db['id']})")
                    else:
                        print("No databases found")
                
                elif command.startswith('summarize '):
                    db_id = command.split(' ', 1)[1]
                    print("🧠 Analyzing database...")
                    summary = self.summarize_database(db_id)
                    print(f"\n📝 Summary:\n{summary}")
                
                elif command.startswith('ask '):
                    question = command.split(' ', 1)[1]
                    print("🤔 Thinking...")
                    answer = self.ask_about_notion(question)
                    print(f"\n💡 Answer:\n{answer}")
                
                else:
                    print("Unknown command. Try 'databases', 'summarize <db_id>', 'ask <question>', or 'quit'")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                self.logger.error(f"An error occurred in interactive mode: {e}")

def main():
    """Main function"""
    print("🚀 Starting Notion AI Agent...")
    
    try:
        agent = NotionAgent()
        
        print("\n🔍 Testing connections...")
        if not agent.test_connection():
            print("\n❌ Setup incomplete. Please fix the issues above.")
            sys.exit(1)
        
        agent.interactive_mode()

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
