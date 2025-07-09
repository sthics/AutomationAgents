"""
Notion AI Agent - Main Script
A simple AI agent that connects to Notion and uses local models
"""

import os
import sys
from dotenv import load_dotenv
from notion_client import Client
import requests
import json
from datetime import datetime

load_dotenv()

class NotionAIAgent:
    def __init__(self):
        self.notion_token = os.getenv('NOTION_TOKEN')
        if not self.notion_token:
            print("Error: NOTION_TOKEN not found in .env file")
            sys.exit(1)
        
        self.notion = Client(auth=self.notion_token)
        self.ollama_url = "http://localhost:11434"
        

    def test_notion_connection(self):
        """Test if Notion connection works"""
        try:
            # Try to list databases
            databases = self.notion.search(filter={"property": "object", "value": "database"})
            print(f"Connected to Notion! Found {len(databases['results'])} databases")
            return True
        except Exception as e:
            print(f"Notion connection failed: {e}")
            return False
    
    def test_ollama_connection(self):
        """Test if Ollama is running and has models"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                if models['models']:
                    print(f"Ollama connected! Available models: {[m['name'] for m in models['models']]}")
                    return True
                else:
                    print("Ollama connected but no models found. Run: ollama pull llama2")
                    return False
            else:
                print("Ollama not responding. Make sure to run: ollama serve")
                return False
        except Exception as e:
            print(f"Ollama connection failed: {e}")
            return False
    
    def get_databases(self):
        """Get all accessible databases"""
        try:
            databases = self.notion.search(filter={"property": "object", "value": "database"})
            return databases['results']
        except Exception as e:
            print(f"Error getting databases: {e}")
            return []
    
    def get_database_pages(self, database_id, limit=10):
        """Get pages from a specific database"""
        try:
            pages = self.notion.databases.query(
                database_id=database_id,
                page_size=limit
            )
            return pages['results']
        except Exception as e:
            print(f"Error getting pages: {e}")
            return []
    
    def ask_ai(self, prompt, model="llama2"):
        """Send prompt to local AI model"""
        try:
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(f"{self.ollama_url}/api/generate", json=data)
            if response.status_code == 200:
                return response.json()['response']
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"AI Error: {e}"
    
    def ask_about_notion(self, question):
        """Ask AI about Notion data with context"""
        # Get current database info
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
        
        return self.ask_ai(context)
    
    def summarize_database(self, database_id):
        """Summarize content of a database using AI"""
        pages = self.get_database_pages(database_id)
        if not pages:
            return "No pages found in database"
        
        # Extract basic info from pages
        page_info = []
        for page in pages:
            title = "Untitled"
            if page.get('properties'):
                # Try to find title property
                for prop_name, prop_value in page['properties'].items():
                    if prop_value['type'] == 'title' and prop_value['title']:
                        title = prop_value['title'][0]['text']['content']
                        break
            
            page_info.append({
                'title': title,
                'created': page['created_time'],
                'last_edited': page['last_edited_time']
            })
        
        # Create prompt for AI
        prompt = f"""
        I have a Notion database with {len(pages)} pages. Here's the information:
        
        {json.dumps(page_info, indent=2)}
        
        Please provide a brief summary of this database content and suggest what type of database this might be.
        """
        
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
                print(f"Error: {e}")

def main():
    """Main function"""
    print("🚀 Starting Notion AI Agent...")
    
    agent = NotionAIAgent()
    
    # Test connections
    print("\n🔍 Testing connections...")
    notion_ok = agent.test_notion_connection()
    ollama_ok = agent.test_ollama_connection()
    
    if not notion_ok or not ollama_ok:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        sys.exit(1)
    
    # Start interactive mode
    agent.interactive_mode()

if __name__ == "__main__":
    main()