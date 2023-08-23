import os
import time

from dotenv import load_dotenv
import pandas as pd

from googapi import fetch_gmail_messages, push_to_drive
from chatgpt import process_messages

load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'file_output')
FILE_NAME = "{}.csv".format(time.strftime('%m-%d-%Y'))
FILE_OUT = os.path.join(OUTPUT_DIR, FILE_NAME)
FOLDER_ID = os.getenv("GOGLE_DRIVE_FOLDER_ID")

def main():
    all_messages = []
    all_email_dates = []
    all_sources = []

    args_list = [
        ("Strictly VC", "Massive Fundings", "Sponsored By ..."),
        ("Term Sheet", "VENTURE DEALS", "PRIVATE EQUITY"),
    ]

    for args in args_list:
        messages, email_dates = fetch_gmail_messages(*args)
        all_messages.extend(messages)
        all_email_dates.extend(email_dates)
        for message in messages:
            all_sources.append(args[0])

    df = process_messages(all_messages, all_email_dates, all_sources)
    df.to_csv(FILE_OUT, index=False)
    file_id = push_to_drive(FILE_NAME, FOLDER_ID)
    if file_id:
        print(f"Uploaded file with ID: {file_id}")
    else:
        print("Failed to upload file to Google Drive.")
    df.head()

if __name__ == '__main__':
    main()
