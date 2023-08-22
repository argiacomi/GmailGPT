from gmail import fetch_gmail_messages
from chatgpt import process_messages
import pandas as pd

def main():
    messages = fetch_gmail_messages(list="Strictly VC", header_one="Massive Fundings", header_two="Sponsored By ...")
    print(messages)
    df = process_messages(messages)
    df.head()
    df.to_csv('output.csv', index=False) # Export the DataFrame to a CSV file

if __name__ == '__main__':
    main()