import requests
import xml.etree.ElementTree as ET
import json
import pandas as pd
from colorama import Fore, Back, Style, init
import urllib3
import time
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize colorama for cross-platform color support
init(autoreset=True)

def xml_to_dict(element):
    """
    Recursively convert an XML element to a dictionary.
    """
    if len(element) == 0:
        return element.text
    result = {}
    for child in element:
        child_result = xml_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_result)
        else:
            result[child.tag] = child_result
    return result

def fetch_with_retry(url, headers, max_retries=3, base_delay=5):
    """
    Fetch URL with exponential backoff retry on failure.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code == 200:
                return response
            else:
                print(Fore.YELLOW + f"Attempt {attempt + 1}: Status {response.status_code} for {url}")
        except Exception as e:
            print(Fore.YELLOW + f"Attempt {attempt + 1}: Exception {str(e)} for {url}")
        
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff with jitter
            print(Fore.BLUE + f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    
    return None  # Failed after all retries

# Step 1: Read issue keys from CSV file using pandas (assume 'Issue key' column exists)
csv_file = r"C:\Users\madhait5\Downloads\JIRA 2025-10-27T01_09_33-0600.csv"  # Change this to your CSV file path if needed
try:
    df = pd.read_csv(csv_file)
    if 'Issue key' not in df.columns:
        print(Fore.RED + "Error: 'Issue key' column not found in the CSV file.")
        exit(1)
    issue_keys = df['Issue key'].dropna().astype(str).tolist()  # Extract non-null values as strings
except FileNotFoundError:
    print(Fore.RED + f"Error: CSV file '{csv_file}' not found. Please ensure it exists.")
    exit(1)
except Exception as e:
    print(Fore.RED + f"Error reading CSV file: {str(e)}")
    exit(1)

if not issue_keys:
    print(Fore.RED + "Error: No issue keys found in the 'Issue key' column.")
    exit(1)

# Step 2: Fetch XML for each issue key, convert to dict, and collect in a list
all_data = []
for key in issue_keys:
    url = f"https://jira.it.keysight.com/si/jira.issueviews:issue-xml/{key}/{key}.xml"
    print(Fore.CYAN + f"Fetching: {url}")
    headers = {
        "Cookie": "JSESSIONID=31C04ED58EA8BA46EA22D28444168AEA",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    }
    
    response = fetch_with_retry(url, headers)
    if response:
        try:
            # Attempt to parse XML
            root = ET.fromstring(response.content)
            data = xml_to_dict(root)
            all_data.append({key: data})  # Store as {issue_key: data_dict}
            print(Fore.GREEN + f"Successfully fetched and parsed data for issue: {key}")
        except ET.ParseError as e:
            print(Fore.RED + f"XML parsing error for {key}: {str(e)}")
            # Optionally, save the raw response for debugging
            with open(f"debug_{key}.xml", "w", encoding="utf-8") as f:
                f.write(response.text)
            print(Fore.RED + f"Saved raw response to debug_{key}.xml for inspection.")
    else:
        print(Fore.RED + f"Failed to fetch XML for {key} after retries.")

# Step 3: Convert the collected data to JSON
json_output = json.dumps(all_data, indent=4)

# Step 4: Print the JSON output with colors
print(Fore.CYAN + Style.BRIGHT + "\n=== Fetched and Converted JSON Data ===")
print(Fore.YELLOW + json_output)
print(Fore.CYAN + Style.BRIGHT + "========================================")
