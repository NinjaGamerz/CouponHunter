import requests
from bs4 import BeautifulSoup
import os
import re

# --- CONFIG ---
KEYWORDS = ["hacking", "cyber", "ai", "python", "bug bounty", "nmap", "sqlmap", "linux", "security", "web dev", "ethical"]
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": False}
        requests.post(url, json=payload)

def get_final_link(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        found = re.search(r'https?://[^\s<>"]+udemy\.com/[^\s<>"]+', res.text)
        return found.group(0).split('"')[0].split("'")[0] if found else url
    except:
        return url

def start_scan():
    # 1. THE HEARTBEAT (Tests your connection immediately)
    send_telegram("🚀 *Hunter is Active!* Checking for new hacking/AI coupons...")
    
    sources = [
        "https://couponscorpion.com/category/cyber-security/",
        "https://couponscorpion.com/category/development/",
        "https://www.tutorialbar.com/category/it-software/cyber-security/"
    ]
    
    matches = 0
    for site in sources:
        print(f"🔍 Scraping {site}...")
        try:
            res = requests.get(site, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # This looks for course titles in h3 or h2 tags
            for item in soup.find_all(['h3', 'h2']):
                title = item.get_text().strip()
                link_tag = item.find('a')
                
                if link_tag and any(word.lower() in title.lower() for word in KEYWORDS):
                    post_url = link_tag['href']
                    # Go deeper to get the 'out.php' link
                    inner = requests.get(post_url, headers={'User-Agent': 'Mozilla/5.0'})
                    inner_soup = BeautifulSoup(inner.text, 'html.parser')
                    btn = inner_soup.select_one("a.btn_offer_block")
                    
                    if btn:
                        udemy_link = get_final_link(btn['href'])
                        send_telegram(f"🎁 *MATCH FOUND!*\n\nTitle: {title}\n\n🔗 [ENROLL NOW]({udemy_link})")
                        matches += 1
        except Exception as e:
            print(f"⚠️ Error: {e}")

    if matches == 0:
        print("No matches found this hour.")

if __name__ == "__main__":
    start_scan()