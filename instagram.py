import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
from tqdm import tqdm
from urllib.parse import urlparse
import requests
import re

def get_instagram_followers(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Updated regex to match numbers like "661M", "12.5K", etc.
        match = re.search(r'<meta property="og:description"\s+content="([\d\.]+[MK]?)\s+Followers', response.text)
        if match:
            followers_str = match.group(1)
            return followers_str
        else:
            print("Followers not found in meta tag.")
            return None
    else:
        print(f"Failed to fetch page: {response.status_code}")
    return None

def extract_base_and_domain(full_url: str):
    # Add https:// if missing
    if not full_url.startswith(("http://", "https://")):
        full_url = "https://" + full_url

    parsed = urlparse(full_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}/"
    domain = parsed.netloc
    return domain

def start_browser():
    # Get the current working directory
    dir_path = os.getcwd()

    # Define the profile path
    profile = os.path.join(dir_path, "profile", "wpp")

    # Set up Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument(r"user-data-dir={}".format(profile))
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")  # Use `--headless=new` for better compatibility
    options.add_argument("--window-size=1920,1080")

    # Initialize the Chrome browser with the options
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return browser

def get_followers_count(browser):
    try:
        # Method 1: Look for the specific span structure you provided
        try:
            followers_span = browser.find_element(By.XPATH, "//span[contains(@class, 'x1lliihq') and contains(text(), 'followers')]")
            # Get the span that contains the follower count (with title attribute)
            count_span = followers_span.find_element(By.XPATH, ".//span[@title]")
            follower_count = count_span.get_attribute("title")
            if follower_count:
                print(f"🔍 Debug - Found followers via span structure: {follower_count}")
                return follower_count
        except:
            pass
        
        # Method 2: Look for span with title attribute that contains numbers
        try:
            title_spans = browser.find_elements(By.XPATH, "//span[@title and contains(following-sibling::text()[1], 'followers') or contains(../text(), 'followers')]")
            for span in title_spans:
                title = span.get_attribute("title")
                if title and any(char.isdigit() for char in title):
                    print(f"🔍 Debug - Found followers via title attribute: {title}")
                    return title
        except:
            pass
        
        # Method 3: Look for any span with title containing numbers near "followers" text
        try:
            followers_elements = browser.find_elements(By.XPATH, "//*[contains(text(), 'followers')]")
            for element in followers_elements:
                # Look for spans with title attribute in the same area
                nearby_spans = element.find_elements(By.XPATH, ".//span[@title] | ./preceding-sibling::*//span[@title] | ./following-sibling::*//span[@title]")
                for span in nearby_spans:
                    title = span.get_attribute("title")
                    if title and any(char.isdigit() for char in title):
                        print(f"🔍 Debug - Found followers via nearby span: {title}")
                        return title
        except:
            pass
        
        # Method 4: Original method - Find all <li> elements
        try:
            li_elements = browser.find_elements(By.TAG_NAME, "li")
            for li in li_elements:
                if "followers" in li.text.lower():
                    # Extract text like "27.4K followers"
                    follower_text = li.text.split()[0]
                    print(f"🔍 Debug - Found followers via li method: {follower_text}")
                    return follower_text
        except:
            pass
        
        # Method 5: Look for any element containing "followers" and extract numbers
        try:
            followers_elements = browser.find_elements(By.XPATH, "//*[contains(text(), 'followers')]")
            for element in followers_elements:
                text = element.text
                if text:
                    # Try to extract the number part before "followers"
                    import re
                    match = re.search(r'([\d,\.]+[KkMm]?)\s*followers', text, re.IGNORECASE)
                    if match:
                        follower_count = match.group(1)
                        print(f"🔍 Debug - Found followers via regex: {follower_count}")
                        return follower_count
        except:
            pass
            
        print("🔍 Debug - No followers count found with any method")
        return None
        
    except Exception as e:
        print("Error extracting followers:", e)
        return None

def get_google_search(account_name):
    api_key = os.getenv("SCRAPINGDOG_API_KEY")
    url = "https://api.scrapingdog.com/google/"
    params = {
        "api_key": api_key,
        "query": account_name + " instagram",
        "results": 1,
        "page": 0
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        links = []

        # Collect Instagram links from organic results
        for result in data.get('organic_results', []):
            link = result.get('link', '')
            if 'instagram.com' in link:
                links.append(link)
        return links

def get_insta_info(account_name):
    browser = start_browser()
    browser.get(account_name)
    time.sleep(0.5)  # Wait for the page to load
    followers = get_followers_count(browser)
    browser.quit()
    return followers

def instagram(csv_file):
    print(f"🔍 Debug - Starting instagram function with file: {csv_file}")
    
    df = pd.read_csv(csv_file, delimiter=';', encoding="latin1")
    print(f"🔍 Debug - DataFrame loaded. Shape: {df.shape}")
    print(f"🔍 Debug - Columns: {df.columns.tolist()}")
    
    # Check if required columns exist
    if "IG" not in df.columns:
        print("⚠️  Warning - 'IG' column not found in DataFrame!")
    
    first_100_websites = df["Website"].head(500).tolist()

    for i, website in tqdm(enumerate(first_100_websites), total=len(first_100_websites), desc="Processing websites"):
        print(f"\n🔍 Debug - Processing website {i}: {website}")
        
        if pd.isna(website) or not isinstance(website, str):
            print(f"⚠️  Skipping invalid website at index {i}: {website}")
            continue

        try:
            existing_ig = df.at[i, "IG"]
            print(f"🔍 Debug - Existing IG value at row {i}: '{existing_ig}' (type: {type(existing_ig)})")
            
            intagram_followers = None

            if pd.notna(existing_ig) and isinstance(existing_ig, str) and existing_ig.startswith("http"):
                print(f"🔍 Debug - Using existing IG link: {existing_ig}")
                # IG already exists, use it directly
                followers = get_instagram_followers(existing_ig)
                print(f"🔍 Debug - get_instagram_followers returned: {followers}")
                
                if followers is not None:
                    intagram_followers = followers
                    print(f"✅ Found {followers} followers at {existing_ig}")
                else:
                    print(f"🔍 Debug - get_instagram_followers failed, trying get_insta_info")
                    intagram_followers = get_insta_info(existing_ig)
                    print(f"🔍 Debug - get_insta_info returned: {intagram_followers}")
            else:
                # IG not found, do search
                domain = extract_base_and_domain(website)
                print(f"🔍 Debug - Extracted domain: {domain}")
                
                links = get_google_search(domain)
                print("🔍 Trying Instagram links from Google:", links)

                for j, link in enumerate(links):
                    print(f"🔍 Debug - Trying link {j+1}/{len(links)}: {link}")
                    followers = get_instagram_followers(link)
                    print(f"🔍 Debug - get_instagram_followers for {link} returned: {followers}")
                    
                    if followers is not None:
                        intagram_followers = followers
                        print(f"🔍 Debug - Setting IG column at row {i} to: {link}")
                        df.at[i, "IG"] = link  # update IG column with found link
                        print(f"✅ Found {followers} followers at {link}")
                        break

                if intagram_followers is None and links:
                    print(f"🔍 Debug - No followers found, using fallback with first link: {links[0]}")
                    intagram_followers = get_insta_info(links[0])
                    df.at[i, "IG"] = links[0]  # fallback: update with first link
                    print(f"🔁 Fallback followers using get_insta_info: {intagram_followers}")

            print(f"🔍 Debug - Final instagram_followers value: {intagram_followers}")
            print(f"🔍 Debug - Setting 'IG volgers' at row {i} to: {intagram_followers}")
            df.at[i, "IGfollowers"] = intagram_followers
            
            # Verify the update
            print(f"🔍 Debug - Verification - IG volgers at row {i}: {df.at[i, 'IGfollowers']}")
            print(f"🔍 Debug - Verification - IG at row {i}: {df.at[i, 'IG']}")

        except Exception as e:
            print(f"❌ Error processing {website}: {e}")
            print(f"🔍 Debug - Setting 'IG volgers' at row {i} to None due to error")
            df.at[i, "IGfollowers"] = None
    
    print(f"\n🔍 Debug - Before saving - DataFrame shape: {df.shape}")
    print(f"🔍 Debug - Sample of IG column: {df['IG'].head().tolist()}")
    print(f"🔍 Debug - Sample of IG volgers column: {df['IGfollowers'].head().tolist()}")
    
    # Save the updated data
    df.to_csv(csv_file, sep=';', index=False)
    print(f"✅ Done. Results saved to {csv_file}")



############################### Saving Instagram Profile ###########################################

# if __name__ == "__main__":
#     print("Saving Profile...")
#     browser = start_browser()
#     instagram_profile = browser.get("https://www.instagram.com/leomessi/")
#     time.sleep(1000)
#     browser.quit()