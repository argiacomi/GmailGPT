from base64 import urlsafe_b64decode
import functools
import os.path
import re
import time

from bs4 import BeautifulSoup
from tqdm import tqdm

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def extract_text(msg, header_one, header_two):
    """Extracts the text between the specified headers from the message."""
    for part in msg['payload']['parts']:
        if part['mimeType'] == 'text/html':
            data = part['body']['data']
            content = urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')

            # Convert the HTML content to plain text using BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text()

            # Find the text between the two headers using regular expressions
            pattern = fr"{header_one}(.*?){header_two}"
            matches = re.findall(pattern, text_content, re.DOTALL)

            if matches:
                return re.sub(r'\n+', '\n', matches[0].strip()) # Remove multiple consecutive newline characters
    return ""

@functools.lru_cache(maxsize=100)
def fetch_gmail_messages(list, header_one, header_two):
    """Fetches messages labeled StrictlyVC from my gmail account"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    messages_list = []
    try:
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        label_id = None
        for label in labels:
            if label['name'] == list:
                label_id = label['id']
                break

        if not label_id:
            print('Label "{}" not found'.format(list))
            return

        # Fetch the first 10 messages, extract the text, and append it to the cumulative object
        results = service.users().messages().list(userId='me', labelIds=[label_id], maxResults=250).execute()
        messages = results.get('messages', [])
        time.sleep(1)

        for i, message in tqdm(enumerate(messages), desc="Fetching messages", total=len(messages)):
            if i > 0 and i % 49 == 0:
                time.sleep(1) # Pause for 1 second every 50 API calls to avoid rate limits
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            message_text = extract_text(msg, header_one, header_two) + "\n\n"
            if message_text:
                messages_list.append(message_text)

    except HttpError as error:
        print(f'An error occurred: {error}')

    return messages_list
