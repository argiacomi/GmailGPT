from gmail import fetch_gmail_messages
from chatgpt import process_messages
import pandas as pd

def main():
    messages = fetch_gmail_messages(list="Strictly VC", header_one="Massive Fundings", header_two="Sponsored By ...")
    df = process_messages(messages)
    print("\nDataFrame:")
    print(df.head())
    df.to_csv('output.csv', index=False) # Export the DataFrame to a CSV file
    df.to_excel('output.xlsx', index=False) # Export the DataFrame to an Excel file

if __name__ == '__main__':
    main()