import requests
from bs4 import BeautifulSoup
import os
import json
import re

# --- CONFIGURATION ---
HISTORY_FILE = "memory.json"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# The Massive Keyword List
KEYWORDS = [
    "hacking", "cyber", "python", "bug bounty", "nmap", "sqlmap", "linux", "security", 
    "penetration", "web dev", "ethical", "forensics", "malware", "red teaming", 
    "owasp", "wireshark", "reverse engineering", "network", "cisco", "ccna", "bash", 
    "powershell", "exploit", "ctf", "kali", "metasploit", "privilege escalation",
    "social engineering", "osint", "android security", "iot security"
]

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def send_telegram(title, link):
    if TOKEN and CHAT_ID:
        text = f"🔥 *100% FREE FOUND!*\n\n🛡️ *{title}*\n\n🔗 [GET IT NOW]({link})"
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": False}
        try:
            requests.post(url, json=payload)
        except:
            pass

def get_real_udemy_link(url):
    """Digs through the intermediate page to find the clean Udemy link"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        
        # Look for the Udemy URL pattern in the HTML
        found = re.search(r'https?://[^\s<>"]+udemy\.com/[^\s<>"]+', res.text)
        if found:
            clean = found.group(0).split('"')[0].split("'")[0]
            return clean
        return url
    except:
        return url

def is_strictly_free(title):
    """The Gatekeeper: Only allows explicit 100% or Free titles"""
    t = title.lower()
    if "100%" in t or "free" in t:
        return True
    return False

def start_scan():
    print("🚀 Starting Ruthless Hunter V8...")
    history = load_history()
    new_finds = 0
    
    # We prioritize categories that are most likely to have 100% off deals
    sources = [
        "https://couponscorpion.com/category/cyber-security/",
        "https://couponscorpion.com/category/development/",
        "https://www.tutorialbar.com/category/it-software/cyber-security/",
        "https://www.tutorialbar.com/category/it-software/network-security/"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for site in sources:
        print(f"🔍 Scanning: {site}")
        try:
            res = requests.get(site, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Find all potential courses
            articles = soup.find_all('article') # CouponScorpion uses <article>
            if not articles:
                # Fallback for TutorialBar
                articles = soup.find_all('div', class_='ml-item')

            for article in articles:
                # Try to find the title tag (h2 or h3)
                title_tag = article.find(['h3', 'h2'])
                if not title_tag: continue
                
                title = title_tag.get_text().strip()
                link_tag = article.find('a')
                if not link_tag: continue
                
                post_link = link_tag['href']

                # --- FILTER 1: KEYWORDS ---
                if not any(k in title.lower() for k in KEYWORDS):
                    continue

                # --- FILTER 2: HISTORY (DUPLICATES) ---
                if post_link in history:
                    continue 

                # --- FILTER 3: STRICT 100% CHECK ---
                # If the title doesn't say "100%" or "Free", we kill it immediately.
                if not is_strictly_free(title):
                    print(f"💰 Rejected (Likely Paid): {title}")
                    continue

                # If we survived all filters, let's get the link
                print(f"✅ Processing: {title}")
                
                # Dig deeper to find the button
                try:
                    inner = requests.get(post_link, headers=headers, timeout=10)
                    inner_soup = BeautifulSoup(inner.text, 'html.parser')
                    
                    # Double check inner page for price cues if possible
                    if "$1" in inner_soup.get_text() or "$9" in inner_soup.get_text():
                        # Sometimes they hide the price, but if we see a $ sign, risky.
                        # But since we passed the Title check, we usually trust it.
                        pass

                    btn = inner_soup.select_one("a.btn_offer_block")
                    if btn:
                        final_link = get_real_udemy_link(btn['href'])
                        send_telegram(title, final_link)
                        
                        # Add to memory immediately so we don't send it again next loop
                        history.append(post_link)
                        new_finds += 1
                        
                except Exception as e:
                    print(f"⚠️ Link Error: {e}")

        except Exception as e:
            print(f"⚠️ Site Error: {e}")

    # Save memory to file
    save_history(history)
    print(f"🏁 Scan complete. Found {new_finds} new courses.")

if __name__ == "__main__":
    start_scan()