import requests
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
from urllib.parse import urljoin
import json
import pandas as pd
from tqdm import tqdm
import re
import time
import concurrent.futures
print("🔧 [INFO] Loading environment variables...")
load_dotenv()
# Load the LLM model
os.environ["GOOGLE_API_KEY"] = os.getenv('GOOGLE_API_KEY')
print("🔐 [INFO] API keys loaded.")
# Load the LLM model
os.environ["GOOGLE_API_KEY"] = os.getenv('GOOGLE_API_KEY')

def get_visible_text_from_url(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Get visible text and clean it
        visible_text = soup.get_text(separator="\n", strip=True)
        return visible_text
    else:
        print(f"Failed to fetch page. Status code: {response.status_code}")
        return None

def get_all_links_from_website(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        links = []
        for tag in soup.find_all("a", href=True):
            full_link = urljoin(url, tag['href'])  # handles relative URLs
            links.append(full_link)
        print(links)
        return links
    else:
        print(f"Failed to fetch page: {response.status_code}")
        return []

def retrieve_links(query):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    system_message = SystemMessage(content=f"""
From the following list of URLs extracted from a website, identify the links that lead to:

1. A contact page (e.g., contains contact information, a contact form, etc.)
2. An "Our Team" or "About Us" page (e.g., team members, staff bios, company information)
3. An Instagram page (e.g., contains a link to the company's Instagram profile)
4. A WhatsApp number (e.g., a link or text that includes a WhatsApp contact number), usually it's tel:... if it doesn't contain a country code just add it
Make sure to not include any mailto:....
Return your answer in the following JSON format:

{{
    "Whatsapp" : "<whatsapp_number_or_null>",
    "IG": "<instagram_page_url_or_null>",
    "contact": "<contact_page_url_or_null>",
    "ourteam": "<our_team_or_about_page_url_or_null>"
}}
""")
    messages = [
        system_message,
        HumanMessage(content=f"Website Text: {query}")
    ]

    print("🤖 [INFO] Sending message to LLM...")
    response = llm(messages)

    if hasattr(response, "content"):
        response_text = response.content.strip()
    elif isinstance(response, dict) and "content" in response:
        response_text = response["content"].strip()
    else:
        response_text = str(response).strip()

    print("✅ [DEBUG] LLM Response:", response_text)
    # Remove everything before the opening curly brace and after the closing one
    start = response_text.find('{')
    end = response_text.rfind('}') + 1  # include the last }
    json_str = response_text[start:end]
    # Now convert to a dictionary
    data = json.loads(json_str)
    return data

def retrieve_info(query):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    system_message = SystemMessage(content=f"""
Analyze the following website pages text and extract the following information in JSON format:

- Vestigingen: Number of physical store locations (if mentioned) if not mentioned, return 1
- Webshop: "Y" if there's a webshop or online shopping, "N" if not
- Opmeringen: A comma-separated list of the business’s specialties or services (mention only services, no descriptions)
- werknemers: If there are any employees mentioned, provide the number, otherwise return 1
- Website Langauge: The language of the website (e.g., "Dutch", "English", etc.)
Output Format:
{{
    "Vestigingen": <number>,
    "webshop": "Y/N",
    "Opmeringen": "service 1, service 2, service 3",
    "werknemers": <number or 1>,
    "Website Language": "<language>",
}}
""")
    home_page = query.get("home", "N/A")
    contact_page = query.get("contact", "N/A")
    team_page = query.get("ourteam", "N/A")
    messages = [
        system_message,
        HumanMessage(content=f"Home Page: {home_page}, Contact Page (This can help with Vestigingen): {contact_page}, Our Team Page (you can extract the werknemers from here ): {team_page}")
    ]

    print("🤖 [INFO] Sending message to LLM...")
    response = llm(messages)

    if hasattr(response, "content"):
        response_text = response.content.strip()
    elif isinstance(response, dict) and "content" in response:
        response_text = response["content"].strip()
    else:
        response_text = str(response).strip()
    
    print("✅ [DEBUG] LLM Response:", response_text)
    # Remove everything before the opening curly brace and after the closing one
    start = response_text.find('{')
    end = response_text.rfind('}') + 1  # include the last }
    json_str = response_text[start:end]
    # Now convert to a dictionary
    data = json.loads(json_str)
    print(data)
    return data
def is_phone_number(value):
    phone_pattern = re.compile(r"^\+?\d[\d\s\-()]{6,}$")
    return bool(phone_pattern.match(value.strip()))

MAX_RETRIES = 3
TIMEOUT_SECONDS = 20


def call_with_retries(func, *args, **kwargs):
    """Retries a function up to MAX_RETRIES if it times out."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                return future.result(timeout=TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            print(f"⚠️ Timeout on attempt {attempt} for function '{func.__name__}'. Retrying...")
        except Exception as e:
            print(f"❌ Error on attempt {attempt} for function '{func.__name__}': {e}")
            break
    print(f"⏭️ Skipping function '{func.__name__}' after {MAX_RETRIES} failed attempts.")
    return None

def AI_retriver(csv_input_file, output_file_path):
    # Read the CSV with the correct delimiter
    df = pd.read_csv(csv_input_file, delimiter=';', encoding="latin1")
    
    # Add the new columns if they don't exist
    if "IG" not in df.columns:
        df["IG"] = ""
    if "Whatsapp" not in df.columns:
        df["Whatsapp"] = ""
    if "Website Language" not in df.columns:
        df['Website Language'] = ""   
    # Get the first 2 websites
    first_100_websites = df["Website"].head(2).tolist()
    
    for i, website in tqdm(enumerate(first_100_websites), total=len(first_100_websites), desc="Processing websites"):
        try:
            if pd.isna(website) or not isinstance(website, str):
                continue
                
            links = get_all_links_from_website(website)
            useful_links = call_with_retries(retrieve_links, links)
            if useful_links is None:
                continue
            useful_links['home'] = website
            
            for page_name, page_url in useful_links.items():
                if not page_url:
                    continue
                if "instagram.com" in page_url:
                    continue
                if is_phone_number(page_url):
                    continue
                text = get_visible_text_from_url(page_url)
                useful_links[page_name] = text
                
            gen_response = call_with_retries(retrieve_info, useful_links)
            if gen_response is None:
                continue
            gen_response['IG'] = useful_links.get('IG', '')
            gen_response['Whatsapp'] = useful_links.get('Whatsapp', '')
            # Update row i in DataFrame with gen_response fields
            for key, value in gen_response.items():
                if key in df.columns:
                    print(f"🔍 Debug - Updating {key} with value: {value}")
                    df.at[i, key] = value
                else:
                    print(f"⚠️  Warning - Key '{key}' not found in DataFrame columns")
            print(f"✅ Successfully processed {website} and updated DataFrame.")
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error processing {website}: {e}")
            continue
    
    # Save the updated DataFrame with semicolon delimiter
    df.to_csv(output_file_path, index=False, sep=';')
    print("✅ Data retrieval completed and saved to", output_file_path)
    