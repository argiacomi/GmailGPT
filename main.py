from gmail import fetch_gmail_messages
from chatgpt import process_messages
import pandas as pd

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

    messages, email_dates = fetch_gmail_messages(list=list_name, header_one=header_one, header_two=header_two)

    start_index = 0
    if search_string:
        start_index = re_start_index(messages, search_string) + 1

    print(f"Starting from index: {start_index}")

    df = process_messages(messages[start_index:], email_dates[start_index:])
    df.to_csv('output.csv', index=False)
    df.head()

if __name__ == '__main__':
    main()
