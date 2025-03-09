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

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'  # Added to allow email deletion
]

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

def get_recent_emails(service, max_results=20, category='promotions'):
    """Get the most recent emails from Gmail.
    
    Args:
        service: Authorized Gmail API service instance.
        max_results: Maximum number of emails to return (default: 20)
        category: Email category to fetch ('promotions', 'social', 'updates', etc.)
    
    Returns:
        List of dictionaries containing email data (subject, sender, snippet)
    """
    try:
        # Get messages from the specified category
        query = f'category:{category}'
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for message in messages:
            msg = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'  # Get full message content
            ).execute()
            
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            
            # Get email body content
            body = ''
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
            
            emails.append({
                'subject': subject,
                'sender': sender,
                'body': body,
                'snippet': msg.get('snippet', '')
            })
            
        return emails
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def delete_emails_from_sender(service, sender_email, max_emails=None):
    """Delete emails from a specific sender.
    
    Args:
        service: Authorized Gmail API service instance.
        sender_email: Email address of the sender whose emails should be deleted
        max_emails: Maximum number of emails to delete (None for no limit)
    
    Returns:
        int: Number of emails deleted
    """
    try:
        total_deleted = 0
        page_token = None
        
        while True:
            # Search for messages from the specific sender
            query = f'from:{sender_email}'
            results = service.users().messages().list(
                userId='me',
                q=query,
                pageToken=page_token,
                maxResults=min(100, max_emails - total_deleted) if max_emails else 100
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                if total_deleted == 0:
                    print(f'No emails found from {sender_email}')
                break
            
            # Report batch size
            batch_size = len(messages)
            print(f'Found {batch_size} more emails from {sender_email}')
            
            # Delete the messages
            for message in messages:
                service.users().messages().trash(
                    userId='me',
                    id=message['id']
                ).execute()
                total_deleted += 1
                
                # Check if we've hit the max_emails limit
                if max_emails and total_deleted >= max_emails:
                    print(f'Reached maximum deletion limit of {max_emails} emails')
                    return total_deleted
            
            print(f'Successfully moved {batch_size} emails to trash')
            
            # Get the next page token
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        print(f'Total emails moved to trash from {sender_email}: {total_deleted}')
        return total_deleted
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return total_deleted  # Return the number deleted before the error

def main():
    """Main function to demonstrate Gmail API functionality."""
    service = get_gmail_service()
    if not service:
        return
    
    try:
        # Get and display recent promotional emails
        print('\nRecent Promotional Emails:')
        recent_emails = get_recent_emails(service, max_results=20, category='promotions')
        for i, email in enumerate(recent_emails, 1):
            print(f"\n{i}. Subject: {email['subject']}")
            print(f"   From: {email['sender']}")
            print(f"   Content:")
            print("   " + "\n   ".join(email['body'].split('\n')[:10]))  # Show first 10 lines of content
            print("   ...")
            
        # Example of deleting emails from a specific sender
        # Uncomment and modify the line below to delete emails
        delete_emails_from_sender(service, "samanthaladuc@substack.com")

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main() 