"""
Email Fetcher Module
Connects to email servers (Gmail/Outlook) via IMAP and fetches tender emails
"""
from typing import List, Dict, Optional
import email
from email.header import decode_header
from email.utils import parseaddr
import os
from datetime import datetime
from imapclient import IMAPClient
import ssl
from config.settings import (
    GMAIL_HOST, GMAIL_PORT, GMAIL_USER, GMAIL_PASSWORD,
    OUTLOOK_HOST, OUTLOOK_PORT, OUTLOOK_USER, OUTLOOK_PASSWORD,
    EMAIL_CHECK_FOLDER, EMAIL_PROCESSED_FOLDER,
    EMAIL_FILTER_SUBJECTS, EMAIL_MARK_AS_READ,
    EMAIL_PROVIDERS
)

# Import OAuth clients
try:
    from agents.rfq_agent.gmail_api_client import GmailAPIFetcher
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False

try:
    from agents.rfq_agent.outlook_graph import OutlookGraphFetcher
    OUTLOOK_GRAPH_AVAILABLE = True
except ImportError:
    OUTLOOK_GRAPH_AVAILABLE = False


class EmailFetcher:
    """Fetch tender emails from Gmail or Outlook via IMAP"""
    
    def __init__(self, provider=None):
        """Initialize email fetcher for specific provider"""
        # Use specified provider or default to first in EMAIL_PROVIDERS
        self.provider = provider if provider else EMAIL_PROVIDERS[0]
        
        if self.provider not in EMAIL_PROVIDERS:
            available = ', '.join(EMAIL_PROVIDERS)
            raise ValueError(f"Invalid provider '{self.provider}'. Available: {available}")
        
        self.client = None
        self.outlook_graph = None  # For Outlook Graph API
        self.gmail_api_client = None  # For Gmail API
        self.using_graph_api = False  # Flag for Outlook Graph API
        self.using_gmail_api = False  # Flag for Gmail API
        
        if self.provider == 'gmail':
            # Check if Gmail OAuth is enabled
            gmail_oauth_enabled = os.getenv('GMAIL_OAUTH_ENABLED', 'false').lower() == 'true'
            if gmail_oauth_enabled and GMAIL_API_AVAILABLE:
                try:
                    self.gmail_api_client = GmailAPIFetcher()
                    self.using_gmail_api = True
                    print("Using Gmail API (OAuth2)...")
                except Exception as e:
                    print(f"[!] Gmail OAuth not configured, falling back to IMAP: {e}")
                    self.using_gmail_api = False
            
            # Standard IMAP settings (used if OAuth not enabled)
            self.host = GMAIL_HOST
            self.port = GMAIL_PORT
            self.username = GMAIL_USER
            self.password = GMAIL_PASSWORD
        elif self.provider == 'outlook':
            # Check if Outlook OAuth is enabled
            outlook_oauth_enabled = os.getenv('OUTLOOK_OAUTH_ENABLED', 'false').lower() == 'true'
            if outlook_oauth_enabled and OUTLOOK_GRAPH_AVAILABLE:
                try:
                    self.outlook_graph = OutlookGraphFetcher()
                    self.using_graph_api = True
                    print("Using OAuth2 for Outlook (Graph API)...")
                except Exception as e:
                    print(f"[!] Outlook OAuth not configured, falling back to IMAP: {e}")
                    self.using_graph_api = False
            
            # Standard IMAP settings (used if OAuth not enabled)
            self.host = OUTLOOK_HOST
            self.port = OUTLOOK_PORT
            self.username = OUTLOOK_USER
            self.password = OUTLOOK_PASSWORD
        else:
            # This case should now be caught by the EMAIL_PROVIDERS check above
            raise ValueError(f"Unsupported email provider: {self.provider}")
        
        self.filter_keywords = [kw.strip() for kw in EMAIL_FILTER_SUBJECTS.split(',')]
        self.check_folder = EMAIL_CHECK_FOLDER
        self.processed_folder = EMAIL_PROCESSED_FOLDER
        self.mark_as_read = EMAIL_MARK_AS_READ.lower() == 'true'
        
    
    def connect(self):
        """Connect to email server"""
        # Gmail API route
        if self.using_gmail_api and self.gmail_api_client:
            return self.gmail_api_client.connect()
        
        # Outlook Graph API route
        if self.using_graph_api and self.outlook_graph:
            return self.outlook_graph.connect()
        
        # Standard IMAP route
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            # Connect to IMAP server
            self.client = IMAPClient(self.host, port=self.port, ssl_context=ssl_context)
            
            # Login
            self.client.login(self.username, self.password)
            
            print(f"[OK] Connected to {self.provider} email")
            return True
        
        except Exception as e:
            print(f"[X] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from email server"""
        if self.using_gmail_api and self.gmail_api_client:
            self.gmail_api_client.disconnect()
            print(f"[OK] Disconnected from {self.provider} (Gmail API)")
            return
        
        if self.using_graph_api and self.outlook_graph:
            self.outlook_graph.disconnect()
            print(f"[OK] Disconnected from {self.provider} (Graph API)")
            return
        
        if self.client:
            try:
                self.client.logout()
                print(f"[OK] Disconnected from {self.provider}")
            except:
                pass
    
    def fetch_tender_emails(self, limit=10):
        """
        Fetch unread emails that match tender keywords
        
        Args:
            limit: Maximum number of emails to fetch
            
        Returns:
            List of email data dicts
        """
        # Gmail API route
        if self.using_gmail_api and self.gmail_api_client:
            return self.gmail_api_client.fetch_tender_emails(limit=limit)
        
        # Outlook Graph API route
        if self.using_graph_api and self.outlook_graph:
            return self.outlook_graph.fetch_tender_emails(limit=limit)
        
        # Standard IMAP route (Gmail or non-OAuth Outlook)
        if not self.client:
            if not self.connect():
                return []
        
        try:
            # Select inbox
            self.client.select_folder(self.check_folder)
            
            # Search for emails from today (including read/unread)
            # For testing: fetch recent emails regardless of read status
            import datetime
            today = datetime.date.today()
            
            # Search for all emails from today
            messages = self.client.search(['SINCE', today])
            
            # Fallback: if no emails today, get recent unread
            if not messages:
                messages = self.client.search(['UNSEEN'])
            
            if not messages:
                print(" No emails found")
                return []
            
            print(f" Found {len(messages)} email(s)")
            
            # Get latest emails first (reverse order)
            messages = list(reversed(messages))
            
            # Limit number of emails to process
            messages = messages[:limit]
            
            print(f" Processing latest {len(messages)} email(s)...\n")
            
            all_emails = []
            
            # Fetch email data
            for msg_id in messages:
                email_data = self._parse_email(msg_id)
                
                if email_data:
                    # We still check if it's a tender for classification internally,
                    # but we return EVERYTHING so it shows up in the logs.
                    is_tender = self._is_tender_email(email_data)
                    email_data['is_tender_heuristic'] = is_tender
                    
                    all_emails.append(email_data)
                    status = "[OK] Tender" if is_tender else "[--] Misc"
                    print(f"  {status}: {email_data['subject'][:60]}...")
                    
                    # Mark as read if configured (and is a tender, or if configured to mark all)
                    # Note: We usually only mark tenders as read automatically, 
                    # but the user requested keeping non-tenders unread.
                    if self.mark_as_read and is_tender:
                        self.client.set_flags([msg_id], ['\\Seen'])
            
            print(f"\n[OK] Fetched {len(all_emails)} email(s) total")
            return all_emails
            
        except Exception as e:
            print(f"[X] Error fetching emails: {e}")
            return []
    
    def _parse_email(self, msg_id: int) -> Optional[Dict]:
        """
        Parse raw email into structured dict
        
        Args:
            msg_id: Email message ID
            
        Returns:
            Email data dict or None
        """
        try:
            # Fetch email data
            response = self.client.fetch([msg_id], ['RFC822'])
            raw_email = response[msg_id][b'RFC822']
            
            # Parse email
            msg = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(msg.get('Subject', ''))
            from_addr = msg.get('From', '')
            sender_name, sender_email = parseaddr(from_addr)
            date_str = msg.get('Date', '')
            
            # Extract body
            body = self._extract_body(msg)
            
            # Extract attachments
            attachments = self._extract_attachments(msg)
            
            return {
                'email_id': f"{self.provider}_{msg_id}",
                'subject': subject,
                'sender': sender_email,
                'sender_name': sender_name,
                'date': date_str,
                'body': body,
                'attachments': attachments,
                'raw_msg_id': msg_id
            }
            
        except Exception as e:
            print(f"  [!]  Error parsing email {msg_id}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ''
        
        decoded_parts = decode_header(header)
        decoded_str = ''
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_str += part
        
        return decoded_str
    
    def _extract_body(self, msg) -> str:
        """Extract email body text"""
        body = ''
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())
        
        return body.strip()
    
    def _extract_attachments(self, msg) -> List[Dict]:
        """
        Extract email attachments
        
        Returns:
            List of {'filename': str, 'content': bytes}
        """
        attachments = []
        
        for part in msg.walk():
            # Check if attachment
            if part.get_content_maintype() == 'multipart':
                continue
            
            if part.get('Content-Disposition') is None:
                continue
            
            filename = part.get_filename()
            if not filename:
                continue
            
            # Decode filename
            filename = self._decode_header(filename)
            
            # Get content
            content = part.get_payload(decode=True)
            
            if content:
                attachments.append({
                    'filename': filename,
                    'content': content
                })
        
        return attachments
    
    def _is_tender_email(self, email_data: Dict) -> bool:
        """
        Check if email is a tender email based on subject keywords
        
        Args:
            email_data: Email data dict
            
        Returns:
            True if tender email
        """
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        
        # Check if any keyword matches
        for keyword in self.filter_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in subject or keyword_lower in body:
                return True
        
        return False
    
    def move_to_processed(self, email_data):
        """
        Move email to processed folder
        
        Args:
            email_data: Email data dict with raw_msg_id
        """
        # Use Gmail API
        if self.using_gmail_api and self.gmail_api_client:
            return self.gmail_api_client.move_to_processed(email_data)
        
        # Use Graph API for Outlook
        if self.using_graph_api and self.outlook_graph:
            return self.outlook_graph.move_to_processed(email_data)
        
        # Otherwise use IMAP
        if not self.client:
            return
        
        try:
            msg_id = email_data['raw_msg_id']
            
            # Try to select/create processed folder
            try:
                self.client.select_folder(self.processed_folder)
            except:
                # Create folder if doesn't exist
                self.client.create_folder(self.processed_folder)
            
            # Copy to processed folder
            self.client.select_folder(self.check_folder)
            self.client.copy([msg_id], self.processed_folder)
            
            # Delete from inbox
            self.client.delete_messages([msg_id])
            self.client.expunge()
            
            print(f"   Moved email to {self.processed_folder}")
            
        except Exception as e:
            print(f"  [!]  Could not move email: {e}")

    def mark_as_read(self, email_data: Dict):
        """
        Mark email as read in the provider
        
        Args:
            email_data: Email data dict with email_id or raw_msg_id
        """
        # Use Gmail API
        if self.using_gmail_api and self.gmail_api_client:
            return self.gmail_api_client.mark_as_read(email_data['email_id'])
        
        # Use Graph API for Outlook
        if self.using_graph_api and self.outlook_graph:
            return self.outlook_graph.mark_as_read(email_data['email_id'])
        
        # Otherwise use IMAP
        if not self.client:
            return
        
        try:
            msg_id = email_data.get('raw_msg_id')
            if not msg_id:
                # Fallback extraction from ID string (provider_id)
                id_parts = email_data['email_id'].split('_')
                if len(id_parts) > 1:
                    msg_id = int(id_parts[-1])
            
            if msg_id:
                self.client.select_folder(self.check_folder)
                self.client.set_flags([msg_id], ['\\Seen'])
                print(f"   Marked email {msg_id} as read")
                
        except Exception as e:
            print(f"  [!]  Could not mark as read: {e}")


# Example usage
if __name__ == "__main__":
    fetcher = EmailFetcher()
    
    if fetcher.connect():
        emails = fetcher.fetch_tender_emails(limit=5)
        
        print(f"\nFetched {len(emails)} tender emails:")
        for email_data in emails:
            print(f"\n- {email_data['subject']}")
            print(f"  From: {email_data['sender']}")
            print(f"  Attachments: {len(email_data['attachments'])}")
        
        fetcher.disconnect()


