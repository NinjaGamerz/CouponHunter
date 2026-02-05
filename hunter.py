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

# Enhanced Keyword List - Expanded hacking/security focus
HACKING_KEYWORDS = [
    "hacking", "hack", "hacker", "hacking ethically", "ethical hacking", "ethical hacker",
    "hack the world", "learn hacking", "become hacker", "how to hack",
    "penetration", "penetration testing", "pentesting", "bug bounty", "bounty hunting",
    "security", "cybersecurity", "cyber security", "cyber attack", "cyber defense",
    "exploit", "exploitation", "vulnerability", "zero day", "payload",
    "malware", "ransomware", "trojan", "worm", "virus",
    "reverse engineering", "reversing", "cracking", "breaking into systems",
    "web hacking", "website hacking", "app hacking", "application hacking",
    "network hacking", "wifi hacking", "wireless hacking", "network penetration",
    "social engineering", "phishing", "spear phishing", "pretexting"
]

SECURITY_KEYWORDS = [
    "osint", "intelligence", "red teaming", "blue team", "purple team",
    "infosec", "information security", "data security", "privacy",
    "ctf", "capture the flag", "wargames", "hacking games",
    "forensics", "digital forensics", "incident response",
    "crypto", "cryptography", "encryption", "decryption"
]

NETWORKING_KEYWORDS = [
    "network", "networking", "ccna", "cisco", "routing", "switching", 
    "tcp/ip", "dns", "http", "https", "ssl", "tls",
    "firewall", "vpn", "proxy", "subnetting", "ipv4", "ipv6",
    "wireshark", "packet", "protocol", "socket", "port", "arp", "bgp"
]

TOOLS_KEYWORDS = [
    "kali", "kali linux", "metasploit", "nmap", "sqlmap", "burp", "burp suite",
    "hydra", "john the ripper", "zap", "owasp zap", "aircrack", "hashcat",
    "mimikatz", "nessus", "openvas", "nikto", "masscan", "airmon", "aircrack-ng",
    "hashcat", "hashater", "john hammer", "pass theHash", "responder",
    "msfvenom", "msfconsole", "beef", "websploit", "sqlninja"
]

CODING_KEYWORDS = [
    "python", "bash", "shell", "shell scripting", "powershell", "batch",
    "linux", "linux terminal", "command line", "terminal", "console",
    "c++", "c#", "java", "javascript", "node.js", "golang", "go", "rust",
    "assembly", "perl", "php", "ruby", "sql", "html", "css", "javascript"
]

ADVANCED_KEYWORDS = [
    "iot security", "iot hacking", "android security", "android hacking",
    "ios security", "blockchain security", "smart contracts",
    "cloud security", "aws security", "azure security", "gcp security",
    "privilege escalation", "lateral movement", "persistence", "post-exploitation",
    "container security", "kubernetes security", "docker security",
    "owasp", "owasp top 10", "zero trust", "defense in depth",
    "threat modeling", "risk assessment", "security audit", "penetration test"
]

ALL_KEYWORDS = SECURITY_KEYWORDS + NETWORKING_KEYWORDS + TOOLS_KEYWORDS + CODING_KEYWORDS + ADVANCED_KEYWORDS

# PREMIUM SOURCES - Tested and reliable
# Note: These sources can be customized - add URLs that work in your region
PREMIUM_SOURCES = {
    # If these sources don't work, add your own reliable coupon/free course URLs
    # Format: "Name": "direct_url_to_coupon_or_free_course_page",
    
    # Example structure - replace with working URLs in your region:
    "Coupon_Source_1": "https://couponscorpion.com/category/cyber-security/",
    "Free_Source_1": "https://www.real.discount/udemy",
    "Coupon_Source_2": "https://couponscorpion.com/category/development/",
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
    """Check if course appears to be 100% off or free"""
    text = (title + " " + content).lower()
    
    # POSITIVE INDICATORS (definitely free)
    free_indicators = [
        "100% off", "100% free", "free course", "completely free", 
        "$0", "free for", "free on udemy", "no cost", "free coupon",
        "coupon code", "free access", "free lecture", "free section",
        "free tutorial", "free download", "free content", "complimentary",
        "gratis", "0$ coupon", "100 percent off"
    ]
    
    for indicator in free_indicators:
        if indicator in text:
            return True
    
    # NEGATIVE INDICATORS (definitely not free) - Be more careful here
    paid_indicators = [
        "save $", "normally $", "was $", "limited time"
    ]
    
    # Only reject if it's clearly a discount (not 100%)
    for paid in paid_indicators:
        if paid in text:
            # Check if it explicitly says "100%" or "free"
            if "100%" not in text and "free" not in text:
                continue  # Don't reject, might be free
            
    # If has keyword + "free" anywhere, ACCEPT
    if "free" in text.lower():
        if any(k.lower() in text for k in ALL_KEYWORDS):
            return True
    
    # If title has keyword + suspicious price pattern, check carefully
    # "hacking 100% off" = accept
    # "hacking course $199" = reject
    if any(k.lower() in title.lower() for k in ALL_KEYWORDS):
        # If it says "$" but not "100%", reject unless it says "free"
        if "$" in text and "100%" not in text and "free" not in text:
            if "$0" not in text:
                return False
    
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
    """Scrape a specific source for free courses - Universal approach"""
    courses_found = []
    
    try:
        log(f"🔍 Scanning: {source_name}")
        res = requests.get(source_url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # UNIVERSAL STRATEGY: Find all links and filter aggressively
        all_links = soup.find_all('a', href=True)
        processed = set()
        
        for link_tag in all_links:
            try:
                href = link_tag.get('href', '').strip()
                link_text = link_tag.get_text(strip=True)
                
                # Skip invalid/duplicate
                if not href or href in processed or len(link_text) < 3:
                    continue
                processed.add(href)
                
                # Must be a valid URL
                if not href.startswith('http'):
                    continue
                
                # Must have udemy in it OR looks like a course post
                is_udemy_direct = 'udemy.com/course' in href
                is_course_post = any(k in href.lower() for k in ['course', 'coupon', 'free', 'lesson'])
                
                if not (is_udemy_direct or is_course_post):
                    continue
                
                # Check if title matches our keywords
                full_text = (link_text + " " + href).lower()
                if not any(k.lower() in full_text for k in ALL_KEYWORDS):
                    continue
                
                # If direct Udemy link, verify
                if is_udemy_direct:
                    title = link_text if link_text else href.split('/course/')[-1].replace('-', ' ')[:60]
                    if not is_truly_free(title, href):
                        continue
                    
                    course_id = extract_course_id(href)
                    
                    courses_found.append({
                        'title': title[:100],
                        'link': href,
                        'source': source_name,
                        'post_link': href
                    })
                    log(f"  ✓ Direct: {title[:55]}")
                    
                else:
                    # It's a post, try to extract real Udemy link
                    title = link_text[:100]
                    
                    try:
                        inner_res = requests.get(href, headers=headers, timeout=10)
                        inner_text = inner_res.text.lower()
                        
                        # Look for Udemy course link in the page
                        udemy_links = re.findall(r'https?://[^\s"\'<>]*udemy\.com/course/[^\s"\'<>]+', inner_res.text)
                        
                        if udemy_links:
                            final_link = udemy_links[0].split('"')[0].split("'")[0]
                            
                            if is_truly_free(title, inner_text):
                                courses_found.append({
                                    'title': title,
                                    'link': final_link,
                                    'source': source_name,
                                    'post_link': href
                                })
                                log(f"  ✓ Found: {title[:55]}")
                    except:
                        pass
                
                time.sleep(0.2)
                
            except Exception as e:
                pass
        
        log(f"  ✅ Complete: {len(courses_found)} courses")
        
    except Exception as e:
        log(f"  ❌ Error: {str(e)[:80]}")
    
    return courses_found

def start_scan():
    """Main scanning function"""
    log("=" * 60)
    log("🚀 Starting CouponHunter V2 (Enhanced - Hacking Focus)...")
    log("=" * 60)
    
    # Check if sources are configured
    if not PREMIUM_SOURCES or len([v for v in PREMIUM_SOURCES.values() if v and v.startswith('http')]) == 0:
        log("⚠️  No working sources configured yet!")
        log("📚 INSTRUCTIONS:")
        log("   1. Find reliable free Udemy course aggregator URLs")
        log("   2. Edit PREMIUM_SOURCES in hunter.py")
        log("   3. Replace URLs with working sites that have 100% free courses")
        log("")
        log("Popular sites to try:")
        log("   • https://couponscorpion.com/category/cyber-security/")
        log("   • https://www.real.discount/udemy")
        log("   • https://www.tutorialbar.com/ (search 'free')")
        log("   • FreeUdemy coupon sites (check your country's version)")
        log("")
        log("Or add direct Udemy coupon URLs you find")
        return
    
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
        if not source_url or not source_url.startswith('http'):
            log(f"⏭️  Skipping invalid source: {source_name}")
            continue
            
        try:
            courses = scrape_source(source_name, source_url, headers)
            all_courses.extend(courses)
        except Exception as e:
            log(f"❌ Error processing {source_name}: {str(e)[:80]}")
        
        time.sleep(1)
    
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
            log(f"❌ Error processing course: {str(e)[:80]}")
    
    # Update history
    history["sent_links"] = list(sent_links)
    history["sent_courses"] = list(sent_courses)
    save_history(history)
    
    log("=" * 60)
    log(f"🏁 Scan complete! Found {new_finds} new free courses")
    log(f"📊 Total unique courses tracked: {len(sent_courses)}")
    log(f"📌 Keywords tracked: {len(ALL_KEYWORDS)} (Heavy on hacking)")
    log("=" * 60)

if __name__ == "__main__":
    start_scan()