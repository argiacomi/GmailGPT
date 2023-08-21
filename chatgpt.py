import os
import time

from dotenv import load_dotenv
import openai
import pandas as pd
import tiktoken
from tqdm import tqdm

# Define the rate limits
token_limit_per_minute = 90000
request_limit_per_minute = 3500

# Initialize counters and timers
tokens_used = 0
requests_made = 0
current_minute = int(time.time() / 60)

# Load your API key from an environment variable or secret management service
load_dotenv()
model = "gpt-3.5-turbo"
openai.api_key = os.getenv("OPENAI_API_KEY")
encoding = tiktoken.encoding_for_model(model)

def reset_counters():
    global tokens_used, requests_made, current_minute
    tokens_used = 0
    requests_made = 0
    current_minute = int(time.time() / 60)

def check_rate_limits():
    global tokens_used, requests_made, current_minute
    new_minute = int(time.time() / 60)
    if new_minute != current_minute:
        reset_counters()
    if tokens_used >= token_limit_per_minute or requests_made >= request_limit_per_minute:
        time.sleep(60 - (time.time() % 60))
        reset_counters()

def generate_prompt(text):
    return """Extract the Company name, Location, Age, Sector, Description, Funding, Total Funding, & Investors where available from the Text. The text may contain entries for multiple Companies:

I expect output in the form of:
Extracted Information: "Company name: FarmWorks; Location: Kenya; Age: N/A; Sector: Agtech; Description: Building clusters of mid-sized farms; Funding: $4.1 million; Total Funding: $5.6 million; Investors: Acumen Resilient Agriculture Fund, Livelihood Impact Fund, Vested World, family offices, angel investors"
"Company name: Kincell Bio; Location: Gainesville, FL; Age: N/A; Sector: Cell-based medicines; Description: Designing and growing a network of production hubs; Funding: $36 million; Total Funding: N/A; Investors: Kineticos Ventures"

Fill in as much info as you can. Do not omit companies, I always need all companies. Do not provide additional commentary, just the extracted information.

Text: {}
Extract:""".format(text)

def make_request(message):
    global tokens_used, requests_made
    check_rate_limits()
    prompt = generate_prompt(message)
    num_tokens = len(encoding.encode(prompt))
    if num_tokens + tokens_used > token_limit_per_minute:
        time.sleep(60 - (time.time() % 60))
        reset_counters()
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    tokens_used += response.usage['total_tokens']
    requests_made += 1
    return response.choices[0].message.content

def extract_to_dataframe(extracted_info):
    key_value_pairs = [item.split(': ') for item in extracted_info.split('; ')] # Split the extracted information into key-value pairs
    data_dict = {pair[0]: pair[1] for pair in key_value_pairs} # Convert the key-value pairs into a dictionary
    return pd.DataFrame([data_dict]) # Convert the dictionary into a DataFrame

def dataframe_entry(result):
    global df
    entries = result.split('\n')
    entries_processed = 0
    for entry in entries:
        if entry.strip():  # Skip empty strings
            try:
                new_entry = extract_to_dataframe(entry)
                if 'df' in globals():
                    df = pd.concat([df, new_entry], ignore_index=True)
                else:
                    df = new_entry
                entries_processed += 1
            except Exception as e:
                print(f"Failed to process entry: {entry}. Error: {e}")
    return entries_processed

def process_messages(messages):
    global df
    for i, message in tqdm(enumerate(messages), desc="Processing messages", total=len(messages)):
        paragraphs = [p for p in message.strip().split('\n') if p]
        result = make_request(message)
        entries_processed = dataframe_entry(result)
        if entries_processed != len(paragraphs):
            print(f"Message ID: {i} has {len(paragraphs)} paragraphs, but {entries_processed} entries were processed.")
    return df