#!/usr/bin/env python3
"""
Gmail Agent
Handles Gmail operations with AI assistance
"""

import os
import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from base_agent import BaseAgent

class GmailAgent(BaseAgent):
    """Gmail AI Agent for email management"""
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self):
        super().__init__("gmail")
        self.credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials/gmail_credentials.json')
        self.token_file = os.getenv('GMAIL_TOKEN_FILE', 'credentials/gmail_token.json')
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Gmail credentials file not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for future use
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info("Gmail authentication successful")
    
    def _test_service_connection(self) -> bool:
        """Test Gmail API connection"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            self.logger.info(f"Connected to Gmail account: {profile.get('emailAddress')}")
            return True
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Gmail account status"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                'email': profile.get('emailAddress'),
                'total_messages': profile.get('messagesTotal', 0),
                'threads_total': profile.get('threadsTotal', 0),
                'status': 'connected'
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_recent_emails(self, max_results: int = 10, query: str = "") -> List[Dict[str, Any]]:
        """Get recent emails"""
        try:
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                # Get full message details
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id']
                ).execute()
                
                # Extract email data
                email_data = self._extract_email_data(msg)
                emails.append(email_data)
            
            self.log_action("get_recent_emails", f"Retrieved {len(emails)} emails")
            return emails
            
        except HttpError as e:
            self.logger.error(f"Error getting emails: {e}")
            return []
    
    def _extract_email_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from Gmail message"""
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
        
        # Extract body
        body = self._extract_body(message['payload'])
        
        return {
            'id': message['id'],
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body[:500],  # Truncate body
            'snippet': message.get('snippet', ''),
            'labels': message.get('labelIds', [])
        }
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract body text from email payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        elif payload['body'].get('data'):
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def summarize_emails(self, emails: List[Dict[str, Any]]) -> str:
        """Summarize a list of emails using AI"""
        if not emails:
            return "No emails to summarize"
        
        # Prepare email data for AI
        email_summaries = []
        for email in emails:
            email_summaries.append({
                'subject': email['subject'],
                'sender': email['sender'],
                'snippet': email['snippet']
            })
        
        prompt = f"""
        Please provide a concise summary of these {len(emails)} emails:
        
        {json.dumps(email_summaries, indent=2)}
        
        Focus on:
        1. Key themes and topics
        2. Important senders
        3. Any action items or urgent matters
        4. Overall tone and priority
        
        Keep the summary brief and organized.
        """
        
        summary = self.ask_ai(prompt)
        self.log_action("summarize_emails", f"Summarized {len(emails)} emails")
        return summary
    
    def extract_action_items(self, emails: List[Dict[str, Any]]) -> str:
        """Extract action items from emails using AI"""
        if not emails:
            return "No emails to analyze"
        
        # Prepare email content for AI
        email_content = []
        for email in emails:
            email_content.append({
                'subject': email['subject'],
                'sender': email['sender'],
                'body': email['body']
            })
        
        prompt = f"""
        Analyze these emails and extract any action items, tasks, or follow-ups needed:
        
        {json.dumps(email_content, indent=2)}
        
        For each action item, provide:
        1. The task description
        2. Who it's from
        3. Any deadlines mentioned
        4. Priority level (high/medium/low)
        
        If no action items are found, say so clearly.
        """
        
        action_items = self.ask_ai(prompt)
        self.log_action("extract_action_items", f"Analyzed {len(emails)} emails for tasks")
        return action_items
    
    def draft_reply(self, email_id: str, context: str = "") -> str:
        """Draft a reply to an email using AI"""
        try:
            # Get original email
            message = self.service.users().messages().get(
                userId='me',
                id=email_id
            ).execute()
            
            original_email = self._extract_email_data(message)
            
            prompt = f"""
            Draft a professional reply to this email:
            
            Subject: {original_email['subject']}
            From: {original_email['sender']}
            Content: {original_email['body']}
            
            Additional context: {context}
            
            Please write a appropriate, professional response. Keep it concise and helpful.
            """
            
            reply = self.ask_ai(prompt)
            self.log_action("draft_reply", f"Drafted reply for email: {original_email['subject']}")
            return reply
            
        except Exception as e:
            self.logger.error(f"Error drafting reply: {e}")
            return f"Error drafting reply: {e}"
    
    def search_emails(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search emails with specific query"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id']
                ).execute()
                
                email_data = self._extract_email_data(msg)
                emails.append(email_data)
            
            self.log_action("search_emails", f"Found {len(emails)} emails for query: {query}")
            return emails
            
        except Exception as e:
            self.logger.error(f"Error searching emails: {e}")
            return []
    
    def get_unread_count(self) -> int:
        """Get count of unread emails"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['UNREAD']
            ).execute()
            
            count = len(results.get('messages', []))
            self.log_action("get_unread_count", f"Found {count} unread emails")
            return count
            
        except Exception as e:
            self.logger.error(f"Error getting unread count: {e}")
            return 0
    
    def interactive_mode(self):
        """Interactive mode for Gmail agent"""
        print(f"\n📧 Gmail Agent - Interactive Mode")
        print("Commands: 'recent', 'unread', 'search <query>', 'summarize', 'actions', 'reply <email_id>', 'quit'")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if command == 'quit':
                    break
                
                elif command == 'recent':
                    emails = self.get_recent_emails(10)
                    if emails:
                        print(f"\n📬 Recent emails ({len(emails)}):")
                        for i, email in enumerate(emails, 1):
                            print(f"{i}. From: {email['sender']}")
                            print(f"   Subject: {email['subject']}")
                            print(f"   Snippet: {email['snippet'][:100]}...")
                            print()
                    else:
                        print("No emails found")
                
                elif command == 'unread':
                    count = self.get_unread_count()
                    print(f"\n📬 You have {count} unread emails")
                
                elif command.startswith('search '):
                    query = command.split(' ', 1)[1]
                    emails = self.search_emails(query)
                    if emails:
                        print(f"\n🔍 Search results for '{query}' ({len(emails)} found):")
                        for i, email in enumerate(emails, 1):
                            print(f"{i}. From: {email['sender']}")
                            print(f"   Subject: {email['subject']}")
                            print()
                    else:
                        print(f"No emails found for '{query}'")
                
                elif command == 'summarize':
                    emails = self.get_recent_emails(10)
                    if emails:
                        print("\n🧠 Generating summary...")
                        summary = self.summarize_emails(emails)
                        print(f"\n📝 Email Summary:\n{summary}")
                    else:
                        print("No emails to summarize")
                
                elif command == 'actions':
                    emails = self.get_recent_emails(10)
                    if emails:
                        print("\n🧠 Extracting action items...")
                        actions = self.extract_action_items(emails)
                        print(f"\n✅ Action Items:\n{actions}")
                    else:
                        print("No emails to analyze")
                
                elif command.startswith('reply '):
                    email_id = command.split(' ', 1)[1]
                    print("\n🧠 Drafting reply...")
                    reply = self.draft_reply(email_id)
                    print(f"\n✉️ Draft Reply:\n{reply}")
                
                else:
                    print("Unknown command. Available: 'recent', 'unread', 'search <query>', 'summarize', 'actions', 'reply <email_id>', 'quit'")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    agent = GmailAgent()
    if agent.test_connection():
        agent.interactive_mode()
    else:
        print("Failed to connect to Gmail")