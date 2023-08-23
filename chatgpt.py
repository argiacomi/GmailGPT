import os
import time
import re

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
MAX_RETRIES = 3
BACKOFF_FACTOR = 5

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
        print("waiting...")
        time.sleep(60 - (time.time() % 60))
        reset_counters()

def is_response_cutoff(response):
    cutoff_patterns = [r"Note", r"extract(ion|ed)?", r"remain(ing)?", r"limit(ation)?s?"]
    return all(re.search(pattern, response, re.IGNORECASE) for pattern in cutoff_patterns)

def generate_prompt(text):
    return """Extract the Company name, Location, Age, Sector, Description, Funding, Total Funding, & Investors where available from the Text. The text may contain entries for multiple Companies:

I expect output in the form of:
1) Company name: Sangon Biotech; Location: Shanghai; Age: 20 years old; Sector: Life sciences research; Description: Provides research services, reagents, and kits for the Chinese life sciences industry; Funding: $290 million; Total Funding: $296.6 million; Investors: Novo Holdings, GL Capital, CPE, Greenwoods Asset Management, Huagai Capital, CDB Venture, China Merchant Health
2) Company name: Viome Life Sciences; Location: Bellevue, WA; Age: 7 years old; Sector: Microbial analysis and personalized nutrition; Description: Sells at-home kits that analyze the microbial composition of stool samples and provide food recommendations as well as supplements and probiotics; Funding: $86.5 million; Total Funding: N/A; Investors: Khosla Ventures, Bold Capital

Fill in as much info as you can. Do not omit companies, I always need all companies. Do not provide additional commentary, just the extracted information. DO NOT DEVIATE FROM THE EXPECTED OUTPUT FORMAT

Text: {}
Extract:""".format(text)

def make_request(message):
    global tokens_used, requests_made

    retries = 0
    full_response = ""
    continuation_prompt = "Please continue the extraction where you left off."
    while retries < MAX_RETRIES:
        print("API Call {} in message, {} total:".format(retries + 1, requests_made + 1))
        try:
            check_rate_limits()
            if full_response == "":
                prompt = generate_prompt(message)
            else:
                prompt = continuation_prompt
            num_tokens = len(encoding.encode(prompt))
            if num_tokens + tokens_used > token_limit_per_minute:
                time.sleep(60 - (time.time() % 60))
                reset_counters()
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "system", "content": "You are a helpful, robotic assistant that always provides responses in the exact format they are asked for."}
                ],
                temperature = 0.01,
            )
            tokens_used += response.usage['total_tokens']
            requests_made += 1
            full_response += response.choices[0].message.content

            if not is_response_cutoff(full_response):
                return full_response

        except (openai.error.APIError, openai.error.Timeout, openai.error.RateLimitError, openai.error.APIConnectionError, openai.error.ServiceUnavailableError) as e:
            retries += 1
            sleep_time = BACKOFF_FACTOR ** retries  # Exponential backoff
            print(f"Error occurred: {str(e)}. Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)
            if retries == MAX_RETRIES:
                print("Max retries limit reached.")
                raise e

def extract_to_dataframe(extracted_info):
    key_value_pairs = [item.split(': ') for item in extracted_info.split('; ')] # Split the extracted information into key-value pairs
    data_dict = {pair[0]: pair[1] if len(pair) > 1 else "N/A" for pair in key_value_pairs} # Convert the key-value pairs into a dictionary
    return pd.DataFrame([data_dict]) # Convert the dictionary into a DataFrame

def dataframe_entry(result):
    # Remove "Extracted Information:" prefix if present
    result = result.replace("Extracted Information:", "").strip()

    entries = result.split('\n')
    entries_processed = 0
    dfs = []


    for entry in entries:
        entry = re.sub(r'^\d+\) ', '', entry)
        entry = entry.strip()
        entry = entry.strip("\"")

        if not entry.startswith("Company name:"):
            print(f"Skipping invalid entry: {entry}")
            continue

        try:
            new_entry = extract_to_dataframe(entry)
            dfs.append(new_entry)
            entries_processed += 1
        except Exception as e:
            print(f"Failed to process entry: {entry}. Error: {e}")
            raise e

    return pd.concat(dfs, ignore_index=True), entries_processed

def process_messages(messages):
    df_total = pd.DataFrame()
    try:
        for i, message in tqdm(enumerate(messages), desc="Processing messages", total=len(messages)):
            paragraphs = [p for p in message.strip().split('\n') if p]
            print("Processing message {}:".format(i+1))
            result = make_request(message)
            df_entry, entries_processed = dataframe_entry(result)
            df_total = pd.concat([df_total, df_entry], ignore_index=True)
            if entries_processed != len(paragraphs)-3:
                print(f"Message ID: {i} has {len(paragraphs)} paragraphs, but {entries_processed} entries were processed.")
            if i % 10 == 0:
              df_total.to_csv('interim.csv', index=False) # Save the data to a CSV file after each message

    except (openai.error.APIError, openai.error.Timeout, openai.error.RateLimitError, openai.error.APIConnectionError, openai.error.ServiceUnavailableError) as e:
        print(f"Error occurred: {str(e)}. Saving current state to 'error_backup.csv'.")
        df_total.to_csv('error_backup.csv', index=False)
    except Exception as e:
        print(f"Unexpected error: {str(e)}. Saving current state to 'error_backup.csv'.")
        df_total.to_csv('error_backup.csv', index=False)
        raise e

    return df_total