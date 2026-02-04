import requests
from bs4 import BeautifulSoup
import re
import os

# --- CONFIGURATION ---
KEYWORDS = ["hacking", "cyber", "ai", "python", "bug bounty", "nmap", "sqlmap", "linux", "security"]
# Add your Telegram details here or use GitHub Secrets (Recommended)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

def get_final_udemy_url(url):
    """Follows the redirect to get the clean Udemy link"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # Step 1: Get the 'out.php' page
        response = requests.get(url, headers=headers, timeout=10)
        # Step 2: Some sites use a Meta Refresh or JS redirect. 
        # We look for the Udemy link in the page content if we didn't get a 302 redirect.
        if "udemy.com" in response.url:
            return response.url
        
        # Search for any Udemy link in the HTML
        found = re.search(r'https?://[^\s<>"]+udemy\.com/[^\s<>"]+', response.text)
        if found:
            return found.group(0).split('"')[0].split("'")[0]
            
        return url # Return original if extraction fails
    except:
        return url

def start_hunter():
    print(f"--- 🕵️ Elite Hacking Hunter V4 ---")
    sources = [
        "https://couponscorpion.com/category/cyber-security/",
        "https://couponscorpion.com/category/development/"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for site in sources:
        print(f"\n🔍 Checking: {site}")
        res = requests.get(site, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for item in soup.find_all('h3', class_='title'):
            title = item.get_text().strip()
            if any(word.lower() in title.lower() for word in KEYWORDS):
                link = item.find('a')['href']
                
                print(f"📌 {title}")
                # Get the intermediate 'out.php' link
                inner_res = requests.get(link, headers=headers)
                inner_soup = BeautifulSoup(inner_res.text, 'html.parser')
                btn = inner_soup.select_one("a.btn_offer_block")
                
                if btn:
                    final_link = get_final_udemy_url(btn['href'])
                    # CLEAN OUTPUT
                    print(f"🔗 Link: {final_link}\n")
                    
                    # SEND TO TELEGRAM
                    msg = f"🎁 *New Free Course!*\n\nTitle: {title}\n\n[Click here to Enroll]({final_link})"
                    send_telegram(msg)

if __name__ == "__main__":
    start_hunter()