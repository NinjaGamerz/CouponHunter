import requests
from bs4 import BeautifulSoup
import os
import re

# --- CONFIG ---
# 1. EXPANDED KEYWORDS (Finds everything)
KEYWORDS = [
    "hacking", "cyber", "python", "bug bounty", "nmap", "sqlmap", "linux", "security", 
    "penetration", "web dev", "ethical", "forensics", "malware", "red teaming", 
    "owasp", "wireshark", "reverse engineering", "network", "cisco", "ccna", "bash", 
    "powershell", "exploit", "ctf", "kali", "metasploit", "privilege escalation"
]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "sent_courses.txt"

def load_history():
    """Loads the list of courses we already sent"""
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_to_history(link):
    """Saves a new link to our memory"""
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{link}\n")

def send_telegram(text):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": False}
        requests.post(url, json=payload)

def get_final_link(url):
    """Follows redirects to get the real Udemy link"""
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        found = re.search(r'https?://[^\s<>"]+udemy\.com/[^\s<>"]+', res.text)
        if found:
            clean = found.group(0).split('"')[0].split("'")[0]
            return clean
        return url
    except:
        return url

def check_if_free(soup):
    """Checks if the coupon page actually says 'Free' or '100% Off'"""
    text_content = soup.get_text().lower()
    if "100% off" in text_content or "price: free" in text_content or "free coupon" in text_content:
        return True
    return False

def start_scan():
    print("🚀 Starting Smart Hunter V7...")
    sent_links = load_history()
    
    # 2. MORE SOURCES (Digs deeper)
    sources = [
        "https://couponscorpion.com/category/cyber-security/",
        "https://couponscorpion.com/category/development/",
        "https://www.tutorialbar.com/category/it-software/cyber-security/",
        "https://www.tutorialbar.com/category/it-software/network-security/"
    ]
    
    new_finds = 0
    
    for site in sources:
        print(f"🔍 Scraping {site}...")
        try:
            res = requests.get(site, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for item in soup.find_all(['h3', 'h2']):
                title = item.get_text().strip()
                link_tag = item.find('a')
                
                # Check 1: Keyword Match
                if link_tag and any(word.lower() in title.lower() for word in KEYWORDS):
                    post_url = link_tag['href']
                    
                    # Check 2: Duplicate Check (Have we seen this specific link before?)
                    if post_url in sent_links:
                        print(f"⏩ Skipping (Already Sent): {title}")
                        continue

                    # Go deeper
                    try:
                        inner = requests.get(post_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                        inner_soup = BeautifulSoup(inner.text, 'html.parser')
                        
                        # Check 3: Price Check (Is it actually 100% off?)
                        if not check_if_free(inner_soup):
                            print(f"💰 Skipping (Not Free): {title}")
                            continue

                        btn = inner_soup.select_one("a.btn_offer_block")
                        if btn:
                            udemy_link = get_final_link(btn['href'])
                            
                            # FINAL SEND
                            print(f"✅ FOUND NEW: {title}")
                            send_telegram(f"🔥 *FREE HACKING COURSE!*\n\n🛡️ *Title:* {title}\n\n🔗 [ENROLL NOW]({udemy_link})")
                            
                            save_to_history(post_url) # Save to memory
                            sent_links.add(post_url)
                            new_finds += 1
                            
                    except Exception as e:
                        print(f"⚠️ Error inside post: {e}")

        except Exception as e:
            print(f"⚠️ Error scanning site: {e}")

    if new_finds == 0:
        print("😴 No NEW 100% off coupons found this run.")

if __name__ == "__main__":
    start_scan()