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
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'creds/credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'creds/token.json')

SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/drive.file',
  'https://www.googleapis.com/auth/drive.metadata'
]

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

def retrieve_google_creds():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

@functools.lru_cache(maxsize=100)
def fetch_gmail_messages(list, header_one, header_two):
    """Fetches messages labeled {list} from gmail account"""

    creds = retrieve_google_creds()

    messages_list = []
    messages_dates = []
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
            timestamp = int(msg['internalDate']) / 1000
            email_date = time.strftime('%m/%d/%Y', time.gmtime(timestamp))
            messages_dates.append(email_date)

    except HttpError as error:
        print(f'An error occurred: {error}')

    return messages_list, messages_dates

def push_to_drive(file_name, folder_id):
    """Pushes completed funding parse to Google Drive"""

    creds = retrieve_google_creds()

    try:
        # create drive api client
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_name,
                                mimetype='text/csv')
        # pylint: disable=maybe-no-member
        file = service.files().create(body=file_metadata, media_body=media,
                                      fields='id').execute()

    except HttpError as error:
        print(F'An error occurred: {error}')
        return None

    return file.get('id')