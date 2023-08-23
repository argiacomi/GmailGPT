import os
import time

import pandas as pd

from googapi import fetch_gmail_messages, push_to_drive
from chatgpt import process_messages

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'file_output')
FILE_NAME = "{}.csv".format(time.strftime('%m-%d-%Y'))

def re_start_index(messages, string="Massive Fundings"):
    for index, message in enumerate(messages):
        if string in message:
            print(f"The index of the message with '{string}' is: {index}")
            return index
    else:
        print(f"The string '{string}' is not present in any of the messages.")
        return 0

def main():
    # Get user inputs
    list_name = input("Enter the list name: ")
    header_one = input("Enter header one: ")
    header_two = input("Enter header two: ")
    search_string = input("Enter the search string (Press Enter to start from default index 0): ")
    file_name_in = input("Enter the output file name (default is {}): ".format(FILE_NAME))
    drive_id = input("Enter the Google Drive Folder ID: ")

    sources = []
    for message in messages:
        sources.append(list_name)

    if file_name_in == "":
        file_out = os.path.join(OUTPUT_DIR, FILE_NAME)
        file_name = FILE_NAME
    else:
        file_out = os.path.join(OUTPUT_DIR, file_name_in)
        file_name = file_name_in

    messages, email_dates = fetch_gmail_messages(list=list_name, header_one=header_one, header_two=header_two)

    start_index = 0
    if search_string:
        start_index = re_start_index(messages, search_string) + 1

    print(f"Starting from index: {start_index}")

    df = process_messages(messages[start_index:], email_dates[start_index:], sources[start_index:])
    df.to_csv(file_out, index=False)
    if drive_id:
        file_id = push_to_drive(file_name, drive_id)
        if file_id:
            print(f"Uploaded file with ID: {file_id}")
        else:
            print("Failed to upload file to Google Drive.")
        df.head()

if __name__ == '__main__':
    main()
