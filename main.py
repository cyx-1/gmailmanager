"""Gmail Manager - A tool for managing Gmail using the Gmail API."""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.mime.text import MIMEText
import os.path
from google.auth.transport.requests import Request
import pickle
import json

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'  # Added to allow email deletion
]

IGNORE_LIST_FILE = 'ignored_senders.json'

def load_ignore_list():
    """Load the list of ignored senders from file."""
    if os.path.exists(IGNORE_LIST_FILE):
        with open(IGNORE_LIST_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_ignore_list(ignore_list):
    """Save the list of ignored senders to file."""
    with open(IGNORE_LIST_FILE, 'w') as f:
        json.dump(list(ignore_list), f, indent=2)

def add_to_ignore_list(sender):
    """Add a sender to the ignore list."""
    ignore_list = load_ignore_list()
    ignore_list.add(sender)
    save_ignore_list(ignore_list)

def get_gmail_service():
    """Get an authorized Gmail API service instance."""
    creds = None
    # The token.pickle file stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def get_next_promotional_email(service, ignore_list=None):
    """Get the next promotional email that's not from an ignored sender.
    
    Args:
        service: Authorized Gmail API service instance.
        ignore_list: Set of email addresses to ignore
    
    Returns:
        Dictionary containing email data (subject, sender, snippet) or None if no emails found
    """
    try:
        page_token = None
        while True:
            # Get batch of messages from promotions category
            results = service.users().messages().list(
                userId='me',
                q='category:promotions',
                maxResults=10,
                pageToken=page_token
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                return None
            
            # Process each message in the batch
            for message in messages:
                # Get the message details with full message to find unsubscribe info
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                
                # Skip this email if sender is in ignore list
                if ignore_list and sender in ignore_list:
                    print(f"Skipping email from {sender} (in ignore list)")
                    continue
                
                # Look for unsubscribe link in headers
                unsubscribe = next((h['value'] for h in headers if h['name'].lower() == 'list-unsubscribe'), None)
                
                # If no unsubscribe in headers, try to find it in the email body
                if not unsubscribe and 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part['mimeType'] == 'text/html' and 'data' in part.get('body', {}):
                            body_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8').lower()
                            # Look for common unsubscribe patterns in HTML
                            unsubscribe_patterns = [
                                'unsubscribe</a>',
                                'opt out</a>',
                                'opt-out</a>'
                            ]
                            for pattern in unsubscribe_patterns:
                                if pattern in body_html:
                                    # Find the closest href before the unsubscribe text
                                    href_start = body_html.rfind('href="', 0, body_html.find(pattern))
                                    if href_start != -1:
                                        href_end = body_html.find('"', href_start + 6)
                                        if href_end != -1:
                                            unsubscribe = body_html[href_start + 6:href_end]
                                            break
                            if unsubscribe:
                                break
                
                # Found a non-ignored email, return it
                return {
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'snippet': msg.get('snippet', ''),
                    'unsubscribe': unsubscribe
                }
            
            # If we've processed all messages in this batch and found nothing,
            # get the next page if available
            page_token = results.get('nextPageToken')
            if not page_token:
                return None  # No more emails to process
            
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def delete_all_emails_from_sender(service, sender, email_id=None):
    """Delete all emails from a specific sender.
    
    Args:
        service: Authorized Gmail API service instance.
        sender: Email address of the sender
        email_id: Optional specific email ID to start with
    """
    try:
        total_deleted = 0
        page_token = None
        
        while True:
            # If we have a specific email_id, delete it first
            if email_id:
                service.users().messages().trash(
                    userId='me',
                    id=email_id
                ).execute()
                total_deleted += 1
                email_id = None  # Clear it so we don't delete it again
            
            # Search for remaining messages from this sender
            query = f'from:{sender}'
            results = service.users().messages().list(
                userId='me',
                q=query,
                pageToken=page_token,
                maxResults=100  # Gmail's maximum batch size
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                break
                
            # Delete this batch of messages
            batch_size = len(messages)
            for message in messages:
                service.users().messages().trash(
                    userId='me',
                    id=message['id']
                ).execute()
                total_deleted += 1
            
            print(f"Moved {batch_size} more emails to trash...")
            
            # Get the next page token
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        print(f"Total emails moved to trash from {sender}: {total_deleted}")
        
    except HttpError as error:
        print(f'An error occurred while deleting: {error}')

def main():
    """Main function to demonstrate Gmail API functionality."""
    service = get_gmail_service()
    if not service:
        return
    
    try:
        # Load the ignore list
        ignore_list = load_ignore_list()
        
        while True:
            # Get next promotional email (excluding ignored senders)
            email = get_next_promotional_email(service, ignore_list)
            if not email:
                print("\nNo more promotional emails found.")
                break
            
            sender = email['sender']
            
            # Display email information
            print(f"\nFound email from: {sender}")
            print(f"Subject: {email['subject']}")
            print(f"Preview: {email['snippet'][:100]}...")
            if email.get('unsubscribe'):
                print(f"Unsubscribe link: {email['unsubscribe']}")
            
            while True:
                response = input(f"\nDo you want to ignore future emails from {sender}? (y/n/q to quit): ").lower()
                if response == 'q':
                    print("Exiting...")
                    return
                elif response in ['y', 'n']:
                    break
                print("Please enter 'y' for yes, 'n' for no, or 'q' to quit")
            
            if response == 'y':
                print(f"Adding {sender} to ignore list...")
                add_to_ignore_list(sender)
            else:
                # Delete all emails from this sender
                delete_all_emails_from_sender(service, sender, email['id'])

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main() 