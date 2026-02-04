import requests
from bs4 import BeautifulSoup
import os
import re

# --- SETTINGS ---
KEYWORDS = ["hacking", "cyber", "ai", "python", "bug bounty", "nmap", "sqlmap", "linux", "security"]
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_to_telegram(course_title, course_link):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Missing Telegram credentials!")
        return
    
    # Clean formatting for Telegram
    message = (
        f"🎁 *NEW FREE COURSE FOUND!*\n\n"
        f"🛡️ *Title:* {course_title}\n\n"
        f"🔗 [ENROLL HERE]({course_link})"
    )
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        requests.post(url, json=payload)
        print(f"✅ Sent to Telegram: {course_title}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def get_direct_link(url):
    """Bypasses the 'out.php' redirection to find the actual Udemy link"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Search for a Udemy link with a coupon attached
        found = re.search(r'https?://[^\s<>"]+udemy\.com/[^\s<>"]+', response.text)
        if found:
            # Clean the link from any trailing quotes or noise
            clean_link = found.group(0).split('"')[0].split("'")[0]
            return clean_link
        return url
    except:
        return url

def start_scan():
    print("🚀 Starting Ninja Hunter V5...")
    sources = [
        "https://couponscorpion.com/category/cyber-security/",
        "https://couponscorpion.com/category/development/"
    ]
    
    for site in sources:
        try:
            res = requests.get(site, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for item in soup.find_all('h3', class_='title'):
                title = item.get_text().strip()
                
                if any(word.lower() in title.lower() for word in KEYWORDS):
                    # Get the intermediate link
                    post_link = item.find('a')['href']
                    
                    # Go into the post to find the 'Get Coupon' button link
                    inner_res = requests.get(post_link, headers={'User-Agent': 'Mozilla/5.0'})
                    inner_soup = BeautifulSoup(inner_res.text, 'html.parser')
                    btn = inner_soup.select_one("a.btn_offer_block")
                    
                    if btn:
                        # Follow the encoded link to get the final Udemy URL
                        final_link = get_direct_link(btn['href'])
                        send_to_telegram(title, final_link)
        except Exception as e:
            print(f"⚠️ Error scanning {site}: {e}")

if __name__ == "__main__":
    start_scan()