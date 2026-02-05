import requests
from bs4 import BeautifulSoup
import os
import json
import re
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# --- CONFIGURATION ---
HISTORY_FILE = "memory.json"
SENT_FILE = "sent_courses.txt"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LOG_FILE = "hunter.log"

# Enhanced Keyword List - Covers security, hacking, coding, testing
SECURITY_KEYWORDS = [
    "hacking", "cyber", "penetration", "ethical hacking", "bug bounty", "security",
    "osint", "red teaming", "social engineering", "exploit", "vulnerability",
    "network security", "web security", "application security", "infosec",
    "ctf", "capture the flag", "forensics", "malware", "reverse engineering"
]

NETWORKING_KEYWORDS = [
    "network", "ccna", "cisco", "routing", "switching", "tcp/ip", "dns",
    "firewall", "vpn", "subnetting", "wireshark", "packet", "protocol"
]

TOOLS_KEYWORDS = [
    "kali", "metasploit", "nmap", "sqlmap", "burp", "hydra", "john",
    "zap", "aircrack", "hashcat", "mimikatz", "nessus", "openvas"
]

CODING_KEYWORDS = [
    "python", "bash", "powershell", "linux", "shell scripting", "c++",
    "java", "javascript", "golang", "rust", "assembly", "php", "nodejs"
]

ADVANCED_KEYWORDS = [
    "iot security", "android security", "ios security", "blockchain security",
    "cloud security", "privilege escalation", "lateral movement", "post-exploitation",
    "container security", "kubernetes", "docker", "owasp", "zero trust"
]

ALL_KEYWORDS = SECURITY_KEYWORDS + NETWORKING_KEYWORDS + TOOLS_KEYWORDS + CODING_KEYWORDS + ADVANCED_KEYWORDS

# PREMIUM SOURCES - Vetted high-quality coupon websites
PREMIUM_SOURCES = {
    "CouponScorpion_Security": "https://couponscorpion.com/category/cyber-security/",
    "CouponScorpion_Dev": "https://couponscorpion.com/category/development/",
    "TutorialBar_Security": "https://www.tutorialbar.com/category/it-software/cyber-security/",
    "TutorialBar_Network": "https://www.tutorialbar.com/category/it-software/network-security/",
    "Real_Discount": "https://www.real.discount/udemy",
    "Giveawayz": "https://giveawayz.com/category/udemy/",
    "FreeCoursesOnline": "https://www.freecoursesonline.me/search?category=Udemy",
    "FreeTutorials24": "https://www.freetutorials24.com/category/udemy-free-courses/",
    "HackTheHacker": "https://www.hackthehacker.com/",
    "UdemyFreeMe": "https://udemyfree.me/",
    "CouponScorpion_Linux": "https://couponscorpion.com/category/linux/",
    "CouponScorpion_Web": "https://couponscorpion.com/category/web-development/",
}

def log(msg):
    """Append to log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass

def load_history():
    """Load previously seen course links to avoid duplicates"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {"sent_links": [], "sent_courses": []}
    return {"sent_links": [], "sent_courses": []}

def save_history(history):
    """Save history to prevent duplicates"""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        log(f"❌ Error saving history: {e}")

def extract_course_id(udemy_url):
    """Extract course ID from Udemy URL for deduplication"""
    try:
        # Udemy URLs like: https://www.udemy.com/course/python-programming-123456
        match = re.search(r'/course/([a-zA-Z0-9\-]+)/?', udemy_url)
        if match:
            return match.group(1)
        # Alternative: use full URL as ID
        return urlparse(udemy_url).path
    except:
        return udemy_url

def is_truly_free(title, content=""):
    """Check if course appears to be 100% off"""
    text = (title + " " + content).lower()
    
    # POSITIVE INDICATORS (definitely free)
    free_indicators = [
        "100% off", "100% free", "free course", "completely free", 
        "$0", "free for limited time", "free on udemy", "no cost",
        "free coupon", "coupon code", "free access", "free course"
    ]
    
    for indicator in free_indicators:
        if indicator in text:
            return True
    
    # NEGATIVE INDICATORS (not free)
    paid_indicators = [
        "paid course", "$9", "$14", "$99", "$199", "save $",
        "45% off", "50% off", "discount", "normally $"
    ]
    
    for paid in paid_indicators:
        if paid in text:
            return False
    
    # If we're unsure but has keyword + "free" in title, include it
    if "free" in title.lower() and any(k in text for k in ALL_KEYWORDS):
        return True
    
    return False

def get_real_udemy_link(url, headers):
    """Extract the actual Udemy link from redirect/coupon pages"""
    try:
        res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Try multiple methods to find Udemy link
        
        # Method 1: Direct regex search
        matches = re.findall(r'https?://(?:www\.)?udemy\.com/course/[^\s"\'<>]+', res.text)
        if matches:
            # Clean up and return first match
            link = matches[0].split('"')[0].split("'")[0]
            return link
        
        # Method 2: Meta tags
        soup = BeautifulSoup(res.text, 'html.parser')
        og_url = soup.find('meta', property='og:url')
        if og_url and 'udemy' in og_url.get('content', ''):
            return og_url['content']
        
        # Method 3: Look for button/link with Udemy URL
        for link_tag in soup.find_all('a'):
            href = link_tag.get('href', '')
            if 'udemy.com/course' in href:
                return href
        
        # If nothing found, return original
        return url
    except Exception as e:
        log(f"⚠️ Error extracting link from {url}: {e}")
        return url

def send_telegram(title, link, source=""):
    """Send course via Telegram with rich formatting"""
    if not TOKEN or not CHAT_ID:
        log(f"⚠️ Telegram not configured (TOKEN/CHAT_ID missing)")
        return False
    
    try:
        course_id = extract_course_id(link)
        text = (
            f"🔥 *100% FREE UDEMY COURSE FOUND!*\n\n"
            f"📚 *{title}*\n\n"
            f"📍 Source: {source}\n"
            f"🔗 [GET IT NOW]({link})\n"
            f"⏰ Found: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            log(f"✅ Telegram sent: {title}")
            return True
        else:
            log(f"❌ Telegram error: {response.text}")
            return False
    except Exception as e:
        log(f"❌ Telegram error: {e}")
        return False

def scrape_source(source_name, source_url, headers):
    """Scrape a specific source for free courses"""
    courses_found = []
    
    try:
        log(f"🔍 Scanning: {source_name} ({source_url})")
        res = requests.get(source_url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Find course containers based on source
        containers = []
        
        if 'couponscorpion' in source_url:
            containers = soup.find_all('article', class_='post')
        elif 'tutorialbar' in source_url:
            containers = soup.find_all('div', class_='ml-item')
        elif 'real.discount' in source_url:
            containers = soup.find_all('div', class_='course-item')
        elif 'giveawayz' in source_url:
            containers = soup.find_all('article', class_='post')
        elif 'freetutorials24' in source_url:
            containers = soup.find_all('div', class_='post')
        elif 'udemyfree' in source_url:
            containers = soup.find_all('div', class_='course')
        else:
            # Generic fallback
            containers = soup.find_all(['article', 'div'], class_=re.compile(r'post|item|course|product'))
        
        log(f"  Found {len(containers)} containers")
        
        for container in containers[:50]:  # Limit to 50 per source
            try:
                # Extract title
                title_tag = container.find(['h2', 'h3', 'a'])
                if not title_tag:
                    continue
                
                title = title_tag.get_text().strip()
                if not title or len(title) < 5:
                    continue
                
                # Extract link
                link_tag = container.find('a', href=True)
                if not link_tag:
                    continue
                
                post_link = link_tag['href']
                if not post_link or not post_link.startswith('http'):
                    continue
                
                # Filter by keywords
                if not any(k.lower() in title.lower() for k in ALL_KEYWORDS):
                    continue
                
                # Quick check for free status in title/preview
                preview_text = container.get_text()[:500]
                if not is_truly_free(title, preview_text):
                    log(f"  💰 Skipped (likely paid): {title[:50]}")
                    continue
                
                # Extract actual Udemy link
                final_link = get_real_udemy_link(post_link, headers)
                
                if 'udemy.com' not in final_link:
                    log(f"  ⚠️ Not Udemy link: {title[:50]}")
                    continue
                
                courses_found.append({
                    'title': title,
                    'link': final_link,
                    'source': source_name,
                    'post_link': post_link
                })
                
                log(f"  ✓ Found: {title[:60]}")
                time.sleep(0.5)  # Be respectful to servers
                
            except Exception as e:
                log(f"  ⚠️ Container error: {e}")
                continue
        
        log(f"  ✅ {source_name} complete: {len(courses_found)} new courses")
        
    except Exception as e:
        log(f"  ❌ {source_name} error: {e}")
    
    return courses_found

def start_scan():
    """Main scanning function"""
    log("=" * 60)
    log("🚀 Starting CouponHunter V2 (Enhanced)...")
    log("=" * 60)
    
    history = load_history()
    sent_links = set(history.get("sent_links", []))
    sent_courses = set(history.get("sent_courses", []))
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    new_finds = 0
    all_courses = []
    
    # Scan all sources
    for source_name, source_url in PREMIUM_SOURCES.items():
        try:
            courses = scrape_source(source_name, source_url, headers)
            all_courses.extend(courses)
        except Exception as e:
            log(f"❌ Error processing {source_name}: {e}")
        
        time.sleep(1)  # Rate limiting
    
    # Deduplicate and send
    sent_this_run = set()
    for course in all_courses:
        try:
            course_id = extract_course_id(course['link'])
            
            # Skip if already sent
            if course['link'] in sent_links or course_id in sent_courses or course_id in sent_this_run:
                log(f"⏭️  Duplicate: {course['title'][:50]}")
                continue
            
            # Send to Telegram
            if send_telegram(course['title'], course['link'], course['source']):
                sent_links.add(course['link'])
                sent_courses.add(course_id)
                sent_this_run.add(course_id)
                new_finds += 1
                
                # Also save to sent_courses.txt
                try:
                    with open(SENT_FILE, "a") as f:
                        f.write(f"{course['link']} | {course['title']} | {course['source']}\n")
                except:
                    pass
        
        except Exception as e:
            log(f"❌ Error processing course: {e}")
    
    # Update history
    history["sent_links"] = list(sent_links)
    history["sent_courses"] = list(sent_courses)
    save_history(history)
    
    log("=" * 60)
    log(f"🏁 Scan complete! Found {new_finds} new free courses")
    log(f"📊 Total unique courses tracked: {len(sent_courses)}")
    log("=" * 60)

if __name__ == "__main__":
    start_scan()